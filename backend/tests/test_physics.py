"""Analytic checks independent of the raster/SPICE implementation."""
import math
import numpy as np
import pytest
from backend.numerics import (
    MOON_RADIUS_M, basis, az_el, plane_fit, great_circle_m,
    circular_interpolate, elevation_from_radii, visibility,
    integrate_battery, longest_interval, refine_zero,
)
from backend.analysis import StudyRequest, build_series, interval_slice, evaluate_series
from backend.geometry import parse_utc


def intervals(*items):
    return [dict(startH=a,endH=b,sunState=s,earthState='visible') for a,b,s in items]


def test_fitted_plane_has_analytic_slope_and_zero_residual():
    row,col=np.indices((10,10))
    z=0.2*col*5+0.3*(-row*5)+1842
    result=plane_fit(z,5)
    assert result['slopeDeg']==pytest.approx(math.degrees(math.atan(math.hypot(.2,.3))),abs=1e-10)
    assert result['roughnessRmsM']<1e-9
    assert result['reliefM']==pytest.approx(22.5)


def test_plane_fit_rejects_missing_data():
    with pytest.raises(ValueError): plane_fit(np.array([[1,np.nan],[2,3]]),5)


@pytest.mark.parametrize('lon,lat',[(0,0),(-137.5,-89.46),(179.9,45),(0,-90)])
def test_local_basis_and_azimuth_convention(lon,lat):
    e,n,u=basis(lon,lat)
    assert np.stack([e,n,u])@np.stack([e,n,u]).T==pytest.approx(np.eye(3),abs=1e-14)
    assert az_el(e,lon,lat)==pytest.approx((90,0),abs=1e-12)
    assert az_el(n,lon,lat)==pytest.approx((0,0),abs=1e-12)
    assert az_el(n+u,lon,lat)==pytest.approx((0,45),abs=1e-12)


def test_great_circle_wrap_and_pole():
    assert great_circle_m(179,0,-179,0)==pytest.approx(MOON_RADIUS_M*math.radians(2))
    assert great_circle_m(0,-90,150,-90)<1e-8
    assert great_circle_m(0,0,180,0)==pytest.approx(math.pi*MOON_RADIUS_M)


def test_exact_spherical_tangent_horizon():
    radius=MOON_RADIUS_M
    height=2
    tangent=math.acos(radius/(radius+height))
    angle=elevation_from_radii(radius,radius+height,tangent)
    assert angle==pytest.approx(-math.degrees(tangent),abs=1e-9)
    # Equal-height terrain 100 km away lies below the tangent plane.
    assert elevation_from_radii(radius,radius,100000/radius)==pytest.approx(-math.degrees(50000/radius),abs=1e-10)


def test_horizon_interpolation_wraps_north():
    assert circular_interpolate(315,np.array([0,90,180,270]),[2,3,4,6])==4
    assert circular_interpolate(-45,np.array([0,90,180,270]),[2,3,4,6])==4


def test_visibility_unknown_and_sensitivity():
    assert visibility(3,1,2)=='visible'
    assert visibility(0,1,2)=='hidden'
    assert visibility(1.5,1,2)=='uncertain'
    assert visibility(float('nan'),1,2)=='unknown'


def test_battery_discharge_and_threshold_times_are_analytic():
    result=integrate_battery(intervals((0,6,'hidden')),100,80,20,40,30)
    assert result['reserveCrossingH']==pytest.approx(2.5)
    assert result['depletionH']==pytest.approx(4)
    assert result['minimumWh']==0
    assert result['points'][-1]['value'] is None


def test_battery_capacity_saturation_adds_exact_kink():
    result=integrate_battery(intervals((0,4,'visible'),(4,6,'hidden')),100,50,10,60,20)
    assert {'hour':1.0,'value':100.0} in result['points']
    assert result['points'][-1]['value']==80
    assert result['minimumWh']==50


def test_battery_uncertain_visibility_gives_two_physical_cases():
    items=intervals((0,2,'uncertain'))
    lo=integrate_battery(items,100,80,20,40,20)
    hi=integrate_battery(items,100,80,20,40,20,True)
    assert lo['points'][-1]['value']==40
    assert hi['points'][-1]['value']==100


def test_battery_does_not_restart_after_depletion():
    result=integrate_battery(intervals((0,2,'hidden'),(2,5,'visible')),100,10,10,100,0)
    assert result['depletionH']==1
    assert result['points'][-1]['value'] is None


def test_zero_initial_charge_is_depleted():
    assert integrate_battery(intervals((0,1,'visible')),100,0,10,50,0)['depletionH']==0


def test_longest_interval_clips_to_mission_and_marks_boundary():
    items=intervals((0,2,'hidden'),(2,3,'visible'),(3,7,'hidden'))
    r=longest_interval(items,lambda p:p['sunState']=='hidden',7)
    assert r==dict(hours=4,startH=3,endH=7,truncated=True)


def test_bisection_is_subsecond_and_rejects_missing_bracket():
    root=refine_zero(lambda h:h*h-2,0,2)
    assert abs(root-math.sqrt(2))*3600<=1
    with pytest.raises(ValueError): refine_zero(lambda h:h*h+2,0,2)


def request(**changes):
    return StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-16T06:00:00Z',**changes)


@pytest.mark.parametrize('changes',[
    dict(minAreaM2=2499),dict(observerHeightM=0),dict(capacityWh=0),
    dict(changeType='invalid'),dict(changeType='time',excludeOriginal=True),
    dict(loadW=float('nan')),
])
def test_invalid_physical_or_search_request_rejected(changes):
    with pytest.raises(ValueError): request(**changes)


def test_naive_time_is_not_assumed_utc():
    with pytest.raises(ValueError): parse_utc('2026-11-15T00:00:00')


class LinearSky:
    def point_at(self,point,height,timestamp):
        return dict(sunAz=90,sunEl=(timestamp-1234)/3600,earthAz=0,earthEl=15)


def test_geometry_transitions_refined_and_mission_clipped_exactly():
    horizon=dict(azimuth=np.array([0,90,180,270]),nominal=np.zeros(4),low=np.full(4,-.1),high=np.full(4,.1))
    series=build_series(LinearSky(),{},2,horizon,0,7200)
    assert series['transitionCount']==2
    mission=interval_slice(series,200,1.2)
    assert sum(i['endH']-i['startH'] for i in mission)==pytest.approx(1.2)
    uncertain=sum(i['endH']-i['startH'] for i in mission if i['sunState']=='uncertain')
    assert uncertain==pytest.approx(.2,abs=2/3600)


def test_missing_mission_geometry_rejected():
    with pytest.raises(ValueError): interval_slice({'times':[0,3600],'states':[dict(sunState='visible',earthState='visible')]},0,2)


def test_unknown_mandatory_ground_never_qualifies():
    req=request(durationH=1,requireKnownGround=True)
    series=dict(times=[0,3600],states=[dict(sunState='visible',earthState='visible')])
    result=evaluate_series({},None,series,0,req,[],[],0)
    assert result['selectedLimitsPass']
    assert not result['qualifies'] and not result['fullyAssessed']
    assert 'Ground bearing strength' in result['unknowns']


def test_changed_source_bytes_are_rejected_before_loading_or_caching(tmp_path,monkeypatch):
    import json
    import backend.terrain as terrain
    import backend.acquire as acquire
    monkeypatch.setattr(terrain,'DATA',tmp_path)
    monkeypatch.setattr(acquire,'ASSETS',{'example.bin':'https://example.invalid/source'})
    (tmp_path/'example.bin').write_bytes(b'changed bytes')
    (tmp_path/'sources.json').write_text(json.dumps({'assets':{'example.bin':{'sha256':'0'*64}}}))
    with pytest.raises(ValueError,match='checksum mismatch'): terrain.Terrain()


def test_missing_visibility_cannot_pass_even_with_abundant_battery():
    req=request(durationH=1)
    series=dict(times=[0,3600],states=[dict(sunState='unknown',earthState='unknown')])
    result=evaluate_series({},None,series,0,req,[],[],0)
    assert not result['qualifies'] and not result['selectedLimitsPass']
    assert 'Missing visibility data' in result['uncertainRequirements'][0]
