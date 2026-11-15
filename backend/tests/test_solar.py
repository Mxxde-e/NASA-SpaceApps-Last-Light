import math
import numpy as np
import pytest
from backend.solar import AU_KM,disc_fraction,incidence_cosine,panel_power
from backend.analysis import StudyRequest,geometry_sample,Engine,evaluate_series
from backend.numerics import integrate_battery

def request(**kwargs):
    return StudyRequest(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T12:00:00Z',**kwargs)

def sample(**kwargs):
    return dict(sunDistanceKm=AU_KM,sunAz=0,sunEl=20,sunHorizonHigh=0,sunHorizonLow=0,sunAngularRadiusDeg=.27)|kwargs

def test_disc_has_correct_area_and_symmetric_partial_visibility():
    assert disc_fraction(-2,1)==0
    assert disc_fraction(0,1)==pytest.approx(.5)
    assert disc_fraction(2,1)==1
    assert disc_fraction(.3,1)+disc_fraction(-.3,1)==pytest.approx(1)
    values=[disc_fraction(x,1) for x in np.linspace(-2,2,99)]
    assert values==sorted(values)

def test_fixed_incidence_uses_panel_normal_not_terrain_slope():
    assert incidence_cosine(0,90,0,0,'fixed')==pytest.approx(1)
    assert incidence_cosine(90,0,90,90,'fixed')==pytest.approx(1)
    assert incidence_cosine(270,0,90,90,'fixed')==pytest.approx(-1)
    assert incidence_cosine(0,30,60,0,'fixed')==pytest.approx(1)

def test_ideal_tracking_and_inverse_square_flux_are_analytic():
    req=request(powerModel='panel',panelAreaM2=2,panelEfficiencyPercent=30,panelLossPercent=10,irradianceAt1AU=1000)
    a=panel_power(sample(),req)
    b=panel_power(sample(sunDistanceKm=2*AU_KM),req)
    assert a['generationLowW']==pytest.approx(540)
    assert b['generationHighW']==pytest.approx(135)
    assert a['incidenceDeg']==0

def test_back_face_produces_no_power():
    req=request(powerModel='panel',panelTracking='fixed',panelTiltDeg=90,panelAzimuthDeg=180)
    assert panel_power(sample(sunAz=0,sunEl=10),req)['generationHighW']==0

def test_partial_solar_disc_can_generate_when_centre_is_hidden():
    req=request(powerModel='panel',panelTracking='sun',irradianceAt1AU=1000,panelEfficiencyPercent=100,panelLossPercent=0)
    result=panel_power(sample(sunEl=-.1,sunHorizonHigh=.1,sunHorizonLow=-.1),req)
    assert 0<result['generationLowW']<result['generationHighW']<=500
    assert result['solarDiscLow']<=result['solarDiscHigh']

def test_power_scales_with_area_efficiency_and_losses():
    base=request(powerModel='panel',panelAreaM2=1,panelEfficiencyPercent=20,panelLossPercent=0,irradianceAt1AU=1000)
    changed=request(powerModel='panel',panelAreaM2=2,panelEfficiencyPercent=10,panelLossPercent=25,irradianceAt1AU=1000)
    assert panel_power(sample(),base)['generationLowW']==200
    assert panel_power(sample(),changed)['generationLowW']==150

def test_interval_power_drives_exact_energy_instead_of_centre_state():
    intervals=[dict(startH=0,endH=1,sunState='hidden',generationLowW=30,generationHighW=50),dict(startH=1,endH=2,sunState='hidden',generationLowW=0,generationHighW=20)]
    lo=integrate_battery(intervals,100,50,10,9999,20)
    hi=integrate_battery(intervals,100,50,10,9999,20,True)
    assert lo['points'][-1]['value']==60
    assert hi['points'][-1]['value']==100

class DiscSky:
    def point_at(self,*args):
        return dict(sunAz=0,sunEl=-.1,sunDistanceKm=AU_KM,sunAngularRadiusDeg=.27,earthAz=90,earthEl=-.5,earthAngularRadiusDeg=1)

def test_earth_any_disc_definition_differs_from_centre():
    horizon=dict(azimuth=np.array([0,90,180,270]),low=np.zeros(4),high=np.zeros(4),nominal=np.zeros(4))
    centre=geometry_sample(DiscSky(),{},2,horizon,0,request(earthVisibilityMode='centre'))
    any_disc=geometry_sample(DiscSky(),{},2,horizon,0,request(earthVisibilityMode='any'))
    assert centre['earthState']=='hidden'
    assert any_disc['earthState']=='visible'
    assert any_disc['earthCentreState']=='hidden'
    assert any_disc['sunState']=='hidden'

def test_missing_panel_samples_cannot_qualify():
    req=request(powerModel='panel',durationH=1)
    series=dict(times=[0,3600],states=[dict(sunState='visible',earthState='visible')])
    result=evaluate_series({},None,series,0,req,[],[],0)
    assert not result['selectedLimitsPass']
    assert any('panel-generation' in message for message in result['uncertainRequirements'])

@pytest.mark.parametrize('kwargs',[dict(powerModel='invented'),dict(panelAreaM2=0),dict(panelEfficiencyPercent=101),dict(panelLossPercent=-1),dict(panelTiltDeg=100),dict(earthVisibilityMode='radio'),dict(minAverageSolarPercent=101)])
def test_invalid_panel_or_dataset_requirements_rejected(kwargs):
    with pytest.raises(ValueError): request(**kwargs)

def test_nasa_unknown_coverage_and_shadow_are_never_accepted_as_pass():
    engine=Engine.__new__(Engine)
    v,u=engine.nasa_requirements({'nasa':dict(available=False)},request())
    assert not v and u
    v,u=engine.nasa_requirements({'nasa':dict(available=True,solarPct=10,earthPct=20,permanentShadow=True)},request(minAverageSolarPercent=30,minAverageEarthPercent=40))
    assert len(v)==3 and not u
