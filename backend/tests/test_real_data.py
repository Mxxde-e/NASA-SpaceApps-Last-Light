"""Integration checks against actual source rasters and independent references."""
from pathlib import Path
import re
import numpy as np
import pytest
import rasterio
from backend.analysis import Engine,StudyRequest,geometry_sample,build_series,evaluate_series
from backend.geometry import parse_utc,SPICE_LOCK
from backend.numerics import basis,great_circle_m
from backend.terrain import DATA
import spiceypy as spice

pytestmark=pytest.mark.data

@pytest.fixture(scope='module')
def service():
    if not (DATA/'sources.json').exists(): pytest.skip('Run python -m backend.acquire for real-data tests.')
    return Engine()


def test_regional_projection_and_pixel_value(service):
    terrain=service.terrain
    x,y=terrain.transform@(1600.5,1600.5)
    lon,lat=terrain.lonlat(x,y)
    assert lon==pytest.approx(-137.5019849,abs=1e-7)
    assert lat==pytest.approx(-89.46315776,abs=1e-8)
    assert terrain.pixel_sample(x,y)==terrain.datasets['z'][1600,1600]
    assert terrain.pixel==5
    assert terrain.roi_z.shape==(1000,1000)
    assert terrain.point(lon,lat)['elevationM']==pytest.approx(1944.762,abs=.01)


@pytest.mark.parametrize('name,old_name',[('surrounding','LDEM_85S_40M.IMG'),('global','LDEM_16.IMG')])
def test_pds_reader_agrees_with_gdal_registration_and_raw_values(service,name,old_name):
    terrain=service.terrain
    directory=DATA/'terrain'
    # Rewrite only the image filename for the independent PDS driver.
    label=directory/f'gdal-test-{name}.lbl'
    text=(directory/f'{name}.lbl').read_text()
    label.write_text(re.sub(old_name,f'{name}.img',text,flags=re.I))
    try:
        with rasterio.open(label) as dataset:
            array=terrain.background if name=='surrounding' else terrain.global_dem
            row,col=(4000,4100) if name=='surrounding' else (1200,3000)
            raw=dataset.read(1,window=((row,row+1),(col,col+1)))[0,0]
            assert raw==array[row,col]
            if name=='surrounding':
                x,y=dataset.xy(row,col)
                info=terrain.background_info
                assert info['sampleOffset']+x/info['pixel']==pytest.approx(col)
                assert info['lineOffset']-y/info['pixel']==pytest.approx(row)
            else:
                assert dataset.width==5760 and dataset.height==2880
            assert dataset.scales[0]==.5
    finally: label.unlink(missing_ok=True)


def test_three_terrain_levels_and_scale_are_used(service):
    coords=[(-11000,-12000),(50000,50000),(220000,220000)]
    units=np.stack([basis(*service.terrain.lonlat(x,y))[2] for x,y in coords])
    height,sigma,resolution=service.terrain.sample_world(units)
    assert np.all(np.isfinite(height))
    assert resolution.tolist()==[5,40,1895.21]
    assert height[0]==pytest.approx(service.terrain.point(*service.terrain.lonlat(-11000,-12000))['elevationM'],abs=.001)
    assert sigma[1]==20 and sigma[2]==250
    assert np.all(np.abs(height)<12000) # catches accidental addition of the radius OFFSET


def test_display_mesh_reconstructs_real_source_elevation_on_curved_moon(service):
    from backend.geometry import surface_position
    terrain=service.terrain
    mesh=terrain.display_mesh(); ref=mesh['reference']
    assert mesh['displaySpacingM']==50 and mesh['sourcePixelM']==5 and mesh['verticalScale']==1
    assert len(mesh['verticesENU'])==100*100*3
    r,c=terrain.r0+504,terrain.c0+504
    x,y=terrain.transform@(c+.5,r+.5)
    lon,lat=terrain.lonlat(x,y)
    local=np.array(mesh['verticesENU']).reshape(-1,3)[50*100+50]
    e,n,u=basis(ref['longitude'],ref['latitude'])
    reconstructed=surface_position(ref['longitude'],ref['latitude'],ref['elevationM'],0)+local@np.stack([e,n,u])
    expected=surface_position(lon,lat,float(terrain.datasets['z'][r,c]),0)
    assert reconstructed==pytest.approx(expected,abs=.001)


def test_missing_mesh_vertices_never_create_filled_triangles(service):
    import copy
    from backend.mesh import build_terrain_mesh
    terrain=copy.copy(service.terrain)
    terrain.datasets=dict(terrain.datasets,z=terrain.datasets['z'].copy())
    terrain.datasets['z'][terrain.r0+4,terrain.c0+4]=np.nan
    mesh=build_terrain_mesh(terrain)
    assert mesh['missingVertices']>=1 and 0 not in mesh['indices']


def test_runtime_evidence_uses_all_50_included_reference_comparisons(service):
    from backend.evidence import geometry_evidence
    evidence=geometry_evidence(service.geometry)
    assert sum(c['comparisons'] for c in evidence['checks'])==50
    assert all(c['passed'] for c in evidence['checks'])


def test_analytic_polar_projection_matches_pyproj(service):
    for lon,lat in [(-137.5,-89.46),(0,-85),(90,-88),(180,-82)]:
        unit=basis(lon,lat)[2]
        factor=2*1737400/(1-unit[2])
        expected=service.terrain.from_lonlat.transform(lon,lat)
        assert [factor*unit[1],factor*unit[0]]==pytest.approx(expected,abs=1e-7)


def test_unsupported_coordinate_does_not_become_zero_terrain(service):
    with pytest.raises(ValueError,match='footprint'): service.terrain.point(0,0)


def test_kernel_coverage_is_enforced(service):
    with pytest.raises(ValueError,match='coverage'):
        service.geometry.validate_date(parse_utc('2055-01-01T00:00:00Z').timestamp())


def test_canonical_naif_frame_example(service):
    # Published in the unmodified moon_080317.tf example, with DE421 and NONE.
    with SPICE_LOCK:
        state,_=spice.spkezr('EARTH',spice.str2et('2008 MAR 17 20:10:00'),'MOON_ME_DE421','NONE','MOON')
    assert state[:3]==pytest.approx([379892.825,33510.118,-12661.5278],abs=.001)


@pytest.mark.parametrize('body',['sun','earth'])
def test_spice_matches_independent_horizons_reference(service,body):
    text=(Path(__file__).parent/f'horizons-{body}.txt').read_text(encoding='utf-8')
    block=text.split('$$SOE')[1].split('$$EOE')[0]
    rows=re.findall(r'(2026-\w+-\d+\s+\d+:\d+)\s+\S*\s+([-\d.]+)\s+([-\d.]+)',block)
    assert len(rows)==25
    from datetime import datetime,timezone
    for date,az,el in rows:
        timestamp=datetime.strptime(date,'%Y-%b-%d %H:%M').replace(tzinfo=timezone.utc).timestamp()
        result=service.geometry.at(-137.50198,-89.46316,1944.761474609375,2,timestamp)
        assert abs((result[body+'Az']-float(az)+180)%360-180)<.0001
        assert abs(result[body+'El']-float(el))<.0001


@pytest.fixture(scope='module')
def search_result(service):
    req=StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-16T06:00:00Z',durationH=24,excludeOriginal=True,exclusionRadiusM=500,requireKnownGround=True)
    return service.search(req)


def test_actual_search_respects_exclusion_and_mandatory_unknowns(search_result):
    assert len(search_result['candidates'])==3
    assert search_result['qualifyingCount']==0
    original=search_result['original']
    candidates=search_result['candidates']
    for i,result in enumerate(candidates):
        assert result['point']['relocationM']>=500
        assert result['point']['relocationM']<=2500
        assert result['scheduleShiftH']!=0
        assert not result['qualifies'] and not result['fullyAssessed']
        assert result['selectedLimitsPass']
        assert result['metrics']['batteryMinimumPercent'][0]>=20
        for other in candidates[:i]:
            assert great_circle_m(result['point']['longitude'],result['point']['latitude'],other['point']['longitude'],other['point']['latitude'])>=500
    assert original['point']['relocationM']==0


def test_horizon_series_metrics_and_energy_share_data(service,search_result):
    req=StudyRequest(**search_result['request'])
    for scenario in [search_result['original'],*search_result['candidates']]:
        h={k:np.asarray(v) for k,v in scenario['horizon'].items()}
        assert np.all(h['low']<=h['nominal']) and np.all(h['nominal']<=h['high'])
        for sample in scenario['samples'][::37]:
            actual=geometry_sample(service.geometry,scenario['point'],req.observerHeightM,h,parse_utc(sample['utc']).timestamp())
            assert actual['sunState']==sample['sunState']
            assert actual['earthState']==sample['earthState']
            assert actual['sunEl']==pytest.approx(sample['sunEl'],abs=1e-6)
        span=sum(i['endH']-i['startH'] for i in scenario['intervals'])
        assert span==pytest.approx(req.durationH)
        visible=sum(i['endH']-i['startH'] for i in scenario['intervals'] if i['sunState']=='visible')
        assert visible==pytest.approx(scenario['metrics']['sunVisibleH'][0])


def test_time_only_search_keeps_original_location(service):
    req=StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T12:00:00Z',durationH=1,changeType='time')
    result=service.search(req)
    assert result['candidates']
    assert result['geometryLocations']==1
    assert all(s['point']['relocationM']==0 and s['scheduleShiftH']==6 for s in result['candidates'])


def test_impossible_requirements_produce_empty_real_result(service):
    req=StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T12:00:00Z',durationH=1,maxSlopeDeg=0,maxReliefM=0)
    result=service.search(req)
    assert not result['candidates'] and result['qualifyingCount']==0


def test_distant_reference_date_does_not_expand_search_sampling(service,monkeypatch):
    import backend.analysis as analysis
    original=analysis.build_series
    spans=[]
    def bounded(*args,**kwargs):
        span=args[5]-args[4]
        assert span<=2*3600
        spans.append(span)
        return original(*args,**kwargs)
    monkeypatch.setattr(analysis,'build_series',bounded)
    req=StudyRequest(landingUTC='2005-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T07:00:00Z',durationH=1,changeType='time')
    service.search(req)
    assert spans==[3600,7200]


def test_precomputed_nasa_values_and_psr_scale(service):
    point=service.point(*service.terrain.lonlat(-11000,-12000))
    assert point['nasa']['solarPct']==pytest.approx(9636*.00004*100)
    assert point['nasa']['earthPct']==pytest.approx(8463*.00004*100)
    assert point['nasa']['permanentShadow'] is False
    assert point['nasa']['shadowPixel']['rawDN']==-20000
    grid=service.screening.grids['shadow']
    row,col=np.unravel_index(np.argmax(grid),grid.shape)
    info=service.screening.labels['shadow']
    x=(col-info['SAMPLE_PROJECTION_OFFSET'])*60
    y=(info['LINE_PROJECTION_OFFSET']-row)*60
    value,*_=service.screening.values(x,y,'shadow')
    assert value==1


@pytest.mark.parametrize('key,oldname',[('solar','AVGVISIB_85S_060M_201608.IMG'),('earth','AVGVISIB_85S_060M_201608_EARTH.IMG'),('shadow','LPSR_85S_060M_201608.IMG')])
def test_precomputed_pds_registration_matches_gdal(service,key,oldname):
    directory=DATA/'screening'; label=directory/f'gdal-test-{key}.lbl'
    label.write_text(re.sub(oldname,f'{key}.img',(directory/f'{key}.lbl').read_text(),flags=re.I))
    try:
        with rasterio.open(label) as dataset:
            x,y=dataset.xy(2729,2345)
            value,row,col,raw=service.screening.values(x,y,key)
            assert (int(row),int(col))==(2729,2345)
            assert raw==dataset.read(1,window=((2729,2730),(2345,2346)))[0,0]
            assert value==pytest.approx(raw*dataset.scales[0]+dataset.offsets[0])
    finally: label.unlink(missing_ok=True)


def test_nasa_filters_run_before_candidate_terrain_and_geometry(service,monkeypatch):
    terrain_calls=[]; original=service.terrain.point
    def count(*args,**kwargs):
        terrain_calls.append(args); return original(*args,**kwargs)
    monkeypatch.setattr(service.terrain,'point',count)
    req=StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T12:00:00Z',durationH=1,minAverageSolarPercent=100)
    result=service.search(req)
    assert not result['candidates']
    assert result['nasaRejectedGridPoints']==result['screenedGridPoints']>0
    assert len(terrain_calls)==1 and result['geometryLocations']==1


def test_real_panel_search_has_bounded_power_and_shared_solar_energy(service):
    req=StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T12:00:00Z',durationH=2,changeType='time',powerModel='panel',earthVisibilityMode='any')
    result=service.search(req)
    assert result['candidates']
    for scenario in [result['original'],*result['candidates']]:
        assert scenario['powerStepSeconds']==60
        lo=sum((p['endH']-p['startH'])*p['generationLowW'] for p in scenario['intervals'])
        hi=sum((p['endH']-p['startH'])*p['generationHighW'] for p in scenario['intervals'])
        assert scenario['solarEnergyWh']==pytest.approx([lo,hi])
        assert 0<=lo<=hi
        assert all(0<=p['generationLowW']<=p['generationHighW']<=p['unshadowedPanelW']+1e-9 for p in scenario['samples'])
