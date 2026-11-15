import pytest
from backend.ranking import rank_candidates
from backend.analysis import StudyRequest


def option(name,battery=40,shift=0,distance=500,outage=10,earth=14,energy=1000,passed=True):
    return ({'name':name,'selectedLimitsPass':passed,'scheduleShiftH':shift,'point':{'relocationM':distance},
             'solarEnergyWh':[energy,energy+10],'metrics':{'batteryMinimumPercent':[battery,battery+5],
             'longestDarkH':[10,11],'longestEarthHiddenH':[max(0,outage-1),outage],'earthVisibleH':[earth,earth+1]}},None)


def names(values,priority): return [s['name'] for s,_ in rank_candidates(values,priority)]


@pytest.mark.parametrize('priority',['schedule','power','communication','relocation'])
def test_failed_or_uncertain_limits_are_never_ranked_even_with_better_metrics(priority):
    assert names([option('failed',battery=100,outage=0,distance=0,passed=False),option('passing')],priority)==['passing']


def test_power_prefers_lower_case_battery_then_lower_case_energy():
    a=option('nearby',battery=30,distance=100,shift=0)
    b=option('battery',battery=60,distance=1500,shift=18)
    c=option('energy',battery=60,distance=2000,shift=24,energy=2000)
    assert names([a,b,c],'power')==['energy','battery','nearby']


def test_communication_prefers_shorter_upper_case_outage_then_visible_hours():
    assert names([option('outage',outage=8,earth=24),option('short',outage=2,earth=18),option('longer-visible',outage=2,earth=21)],'communication')==['longer-visible','short','outage']


def test_schedule_and_relocation_have_explicit_different_priorities():
    items=[option('near',shift=12,distance=100),option('on-time',shift=0,distance=1500),option('earlier',shift=-6,distance=900)]
    assert names(items,'schedule')==['on-time','earlier','near']
    assert names(items,'relocation')==['near','earlier','on-time']


def test_priority_validation_and_backwards_compatible_default():
    args=dict(landingUTC='2026-11-15T06:00:00Z',earliestUTC='2026-11-15T06:00:00Z',latestUTC='2026-11-15T06:00:00Z')
    assert StudyRequest(**args).rankingPriority=='schedule'
    with pytest.raises(ValueError,match='priority'): StudyRequest(**args,rankingPriority='invented')
