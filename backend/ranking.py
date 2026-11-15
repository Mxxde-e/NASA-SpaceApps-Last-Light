"""Deterministic priorities applied only after assessed requirements pass."""

PRIORITIES = {
    'schedule': ['Smallest absolute landing-time shift', 'Shortest relocation', 'Highest lower-case minimum battery'],
    'power': ['Highest lower-case minimum battery', 'Highest lower-case generated energy', 'Shortest upper-case dark interval', 'Smallest absolute landing-time shift', 'Shortest relocation'],
    'communication': ['Shortest upper-case Earth-hidden interval', 'Most lower-case Earth-visible hours', 'Smallest absolute landing-time shift', 'Shortest relocation', 'Highest lower-case minimum battery'],
    'relocation': ['Shortest relocation', 'Smallest absolute landing-time shift', 'Highest lower-case minimum battery'],
}


def ranking_key(scenario, priority):
    m = scenario['metrics']
    shift, distance = abs(scenario['scheduleShiftH']), scenario['point']['relocationM']
    battery = -m['batteryMinimumPercent'][0]
    if priority == 'power':
        return battery, -scenario['solarEnergyWh'][0], m['longestDarkH'][1], shift, distance
    if priority == 'communication':
        return m['longestEarthHiddenH'][1], -m['earthVisibleH'][0], shift, distance, battery
    if priority == 'relocation':
        return distance, shift, battery
    if priority == 'schedule':
        return shift, distance, battery
    raise ValueError('Unknown ranking priority.')


def rank_candidates(candidates, priority):
    # This gate is also enforced here so a new caller cannot rank a failed case.
    return sorted((item for item in candidates if item[0]['selectedLimitsPass']),
                  key=lambda item: ranking_key(item[0], priority))
