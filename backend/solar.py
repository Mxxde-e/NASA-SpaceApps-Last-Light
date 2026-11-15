"""First-order panel power from SPICE distance, pointing, and a finite solar disc."""
import math
import numpy as np

AU_KM=149_597_870.7

def disc_fraction(clearance_deg,radius_deg):
    """Area above a straight local horizon, assuming a uniform-brightness disc."""
    if radius_deg<=0: return float(clearance_deg>0)
    u=max(-1.0,min(1.0,clearance_deg/radius_deg))
    return (math.acos(-u)+u*math.sqrt(max(0,1-u*u)))/math.pi

def incidence_cosine(sun_az,sun_el,tilt,azimuth,tracking):
    # Tilt is from local horizontal: 0 = upward normal; 90 = vertical panel.
    if tracking=='sun': return 1.0
    el,t,da=np.radians([sun_el,tilt,sun_az-azimuth])
    return float(np.clip(np.sin(el)*np.cos(t)+np.cos(el)*np.sin(t)*np.cos(da),-1,1))

def panel_power(sample,request):
    distance=sample['sunDistanceKm']
    cosine=incidence_cosine(sample['sunAz'],sample['sunEl'],request.panelTiltDeg,request.panelAzimuthDeg,request.panelTracking)
    irradiance=request.irradianceAt1AU*(AU_KM/distance)**2
    unshadowed=irradiance*request.panelAreaM2*request.panelEfficiencyPercent/100*(1-request.panelLossPercent/100)*max(0,cosine)
    low=disc_fraction(sample['sunEl']-sample['sunHorizonHigh'],sample['sunAngularRadiusDeg'])
    high=disc_fraction(sample['sunEl']-sample['sunHorizonLow'],sample['sunAngularRadiusDeg'])
    return dict(generationLowW=unshadowed*low,generationHighW=unshadowed*high,
                solarDiscLow=low,solarDiscHigh=high,incidenceDeg=math.degrees(math.acos(cosine)),
                solarIrradianceWm2=irradiance,sunDistanceAU=distance/AU_KM,
                unshadowedPanelW=unshadowed)
