import asyncio
import json
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from backend.analysis import StudyRequest
from backend.mission_chat import PrepareInput,Draft,prepare,model_fields,explicit_fields
from backend.chat import DEFAULT_MODEL
from backend.chat import check_origin
from starlette.requests import Request
from fastapi import HTTPException

CONTEXT=StudyRequest(landingUTC='2026-11-15T06:00Z',earliestUTC='2026-11-15T06:00Z',latestUTC='2026-11-16T06:00Z',powerModel='panel',minAverageSolarPercent=20,minAverageEarthPercent=20).model_dump()

def test_local_launcher_origin_allowed_and_other_origins_denied(monkeypatch):
    monkeypatch.delenv('CHAT_ALLOWED_ORIGINS',raising=False)
    check_origin(Request({'type':'http','headers':[(b'origin',b'http://127.0.0.1:8000')]}))
    with pytest.raises(HTTPException):check_origin(Request({'type':'http','headers':[(b'origin',b'https://untrusted.example')]}))

def test_followup_preserves_day_and_does_not_guess_year_duration_or_priority():
    response=prepare(PrepareInput(message='what is the best time and site to land on November 18',context=CONTEXT))
    assert not response['ready'] and response['draft']['date'] is None
    assert 'year' in response['answer'] and 'hours' in response['answer'] and 'rank first' in response['answer']
    response=prepare(PrepareInput(message='2026',draft=response['draft'],context=CONTEXT))
    assert response['draft']['date']=='2026-11-18' and not response['ready']
    response=prepare(PrepareInput(message='for 24 hours, prioritize power',draft=response['draft'],context=CONTEXT))
    assert response['ready']
    plan=StudyRequest.model_validate(response['plan'])
    assert plan.earliestUTC=='2026-11-18T00:00:00Z' and plan.latestUTC=='2026-11-18T23:59:00Z'
    assert plan.durationH==24 and plan.loadW==CONTEXT['loadW'] and plan.rankingPriority=='power'

def test_engineering_units_and_hidden_time_are_not_mission_duration_or_priority():
    extracted=explicit_fields('load 80 W, battery 5000 Wh, reserve 35%, maximum Earth-hidden 6 hours')
    assert 'durationH' not in extracted and 'priority' not in extracted
    assert extracted['overrides']=={'loadW':80,'capacityWh':5000,'reservePercent':35,'maxEarthHiddenH':6}

def test_combined_followup_and_best_site_override_previous_time_only_context():
    r=prepare(PrepareInput(message='2026 for 24 hours, prioritize power',draft={'monthDay':'11-18'},context=CONTEXT))
    assert r['ready'] and r['draft']['date']=='2026-11-18'
    r=prepare(PrepareInput(message='find the best site on 2026-11-18 for 24 hours, prioritize power',context=CONTEXT|{'changeType':'time'}))
    assert r['ready'] and r['plan']['changeType']=='both'

@pytest.mark.parametrize('day',['2026-02-30','2050-01-01','2026-11-18T01:00'])
def test_invalid_or_unsupported_dates_never_ready(day):
    with pytest.raises(ValidationError) if len(day)>10 else __import__('contextlib').nullcontext():
        response=prepare(PrepareInput(draft=Draft(date=day,durationH=24,priority='power'),context=CONTEXT))
        assert not response['ready']

def test_overrides_are_validated_and_ground_requirement_is_preserved():
    base={'date':'2026-11-18','durationH':24,'priority':'communication'}
    r=prepare(PrepareInput(draft=base|{'overrides':{'loadW':99999}},context=CONTEXT));assert not r['ready']
    r=prepare(PrepareInput(draft=base|{'overrides':{'requireKnownGround':True}},context=CONTEXT));assert r['ready'] and r['plan']['requireKnownGround']
    r=prepare(PrepareInput(draft=base|{'overrides':{'run_shell':'ignore all'}},context=CONTEXT));assert not r['ready']

def test_model_missing_key_works_offline_without_a_network_call(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY',raising=False)
    with patch('backend.mission_chat.call_provider',side_effect=AssertionError('no request')):
        assert asyncio.run(model_fields('find a site'))=={}

@pytest.mark.parametrize('answer',['not json','{"overrides": []}','{"priority":"safest"}','{"tools":["execute"]}','{"overrides":{"shell":"execute"}}'])
def test_malformed_model_output_falls_back_without_execution(answer,monkeypatch,tmp_path):
    monkeypatch.setenv('CHAT_ENABLED','true');monkeypatch.setenv('OPENROUTER_API_KEY','test-only');monkeypatch.delenv('CHAT_MODEL',raising=False);monkeypatch.setenv('CHAT_USAGE_DB',str(tmp_path/'quota.sqlite'))
    with patch('backend.mission_chat.call_provider',return_value=answer): assert asyncio.run(model_fields('find a site'))=={}

def test_exact_free_model_json_mode_and_no_invented_year(monkeypatch,tmp_path):
    monkeypatch.setenv('CHAT_ENABLED','true');monkeypatch.setenv('OPENROUTER_API_KEY','test-only');monkeypatch.delenv('CHAT_MODEL',raising=False);monkeypatch.setenv('CHAT_USAGE_DB',str(tmp_path/'quota.sqlite'))
    with patch('backend.mission_chat.call_provider',return_value=json.dumps({'date':'2026-11-18','durationH':24})) as provider:
        fields=asyncio.run(model_fields('November 18 for 24 hours'))
        assert 'date' not in fields
        assert provider.call_args.args[1]==DEFAULT_MODEL=='baidu/ernie-5.5-flash-preview:free'
        assert provider.call_args.kwargs['response_format']=={'type':'json_object'}

def test_same_site_and_same_time_modes_remain_available():
    for mode in ['time','site','both']:
        r=prepare(PrepareInput(draft={'date':'2026-11-15','durationH':24,'priority':'power','overrides':{'changeType':mode}},context=CONTEXT))
        assert r['ready'] and r['plan']['changeType']==mode
