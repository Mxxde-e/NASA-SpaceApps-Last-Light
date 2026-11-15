# Mission planning chat, voice input and accessibility

The chat has two paths: site-guide explanations and an explicit real-study planner. Scientific results always come from the existing NASA/SPICE engine. The model translates language into proposed inputs; it does not produce candidate coordinates, visibility hours, battery values or qualification decisions.

## Model

The default OpenRouter model is `baidu/ernie-5.5-flash-preview:free`. Its exact ID, zero input/output token pricing, and JSON/structured-output support were checked against the official model catalog on 2026-11-15. Official page: https://openrouter.ai/baidu/ernie-5.5-flash-preview:free . This supports its use as a language interface; it is not a scientific validation of the model. Availability, rate limits and output quality can change. No live authenticated inference was tested because this local environment has no provider key.

`CHAT_MODEL` overrides the default only when deliberately configured. Requests disable provider fallbacks; the app never substitutes a paid model automatically. Plain guide replies have a 400-token output cap; mission JSON extraction has a 600-token cap. Both retain the 64 KiB response limit, fixed HTTPS origin, request timeouts, two concurrent provider slots and persistent global quotas (100 attempts per rolling day, eight per minute). Provider errors are not exposed to visitors. Validated offline parsing and structured date/duration/priority controls remain available without a key or during an outage.

## Planner flow

1. In Real-data study, choose **Plan a real study**, or ask “What is the best time and site to land on November 18?”
2. The planner asks for a year, mission duration and ranking priority rather than inventing them. A partial November 18 date survives a follow-up containing the year. Common engineering units and the three site/time change modes are recognized offline; the optional model can interpret additional named study inputs.
3. Review the UTC landing date, surface hours and priority. All remaining calculation settings are disclosed with names and units; they come from the current mission form plus explicitly interpreted overrides. Change detailed inputs in Mission inspector and review again. Editing a reviewed date/duration/priority disables calculation until another review.
4. **Calculate real options** sends a validated StudyRequest to the existing `/api/search` queue and polls `/api/jobs/{id}`. The service retains its single-analysis concurrency limit, NASA checksums, cache fingerprints and scientific algorithms. Progress, busy/failed states, empty searches and unassessed ground support remain explicit. Stop waiting cancels client polling, not a submitted backend calculation.
5. Result cards display only fields returned by that job: real coordinates, landing UTC, visibility and battery sensitivity ranges. The highest-ranked evaluated option is shown first. Best means highest ranked under the entered priority in this bounded search, not a whole-Moon optimum or a verified safe site.
6. **Autofill & run R1/R2/R3** loads the selected coordinates, UTC and engineering requirements into the mission form and runs that exact plan. It pins the time window to that UTC, uses same-site/time-only evaluation, and disables original exclusion so the chosen point can be evaluated. The chosen option becomes the original plan, with an explanatory status. The selection is consumed once and does not replay on a mode change.

POST `/api/chat/prepare` accepts a bounded message, structured draft and current form context. Extra draft fields, unsupported setting names, invalid dates/priorities and out-of-limit inputs are rejected or require clarification. The optional model requests JSON object output, then server-side validation constrains every proposed setting before calculation. Model text, HTML and tools are never executed. The planner cannot run arbitrary code, access private files or select an endpoint. It covers only the verified Connecting Ridge footprint. Ground strength, sinkage, rock clearance and flight reachability remain unassessed.

## Voice and approved accessibility features

- **Mic / Start voice input** uses the browser's SpeechRecognition or webkitSpeechRecognition API, requires a user click and microphone permission, and fills an editable draft. **Stop** ends dictation; **Send** remains a separate action. Closing/clearing chat, changing data mode or unmounting aborts recognition. Unsupported browsers, denied permission, start errors and no-speech errors leave typed entry available. Browser recognition may send audio to its recognition provider; the notice appears before recording. The app does not record or upload audio to its Python service. Actual microphone transcription was not validated here; lifecycle/error behavior was tested using a recognizer double.
- **Larger text and controls** is optional and persisted in browser local storage. It enlarges workspace/chat text, form controls and help targets; the theme switch remains independent.
- **Skip to mission workspace** and stronger focus outlines support keyboard navigation. Header measurement keeps sticky navigation below a wrapped header.
- **Text summary of terrain, visibility & battery** exposes actual coordinates, slope, relief, cursor conditions, visibility totals, longest hidden intervals, depletion and a semantic table of merged visibility intervals. The table is keyboard-scrollable. These are alternative views of the same numerical result.

Reference for browser speech behavior: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition . Browser support and recognition availability vary; keyboard entry is always retained.

## Activation and deployment

AI is off by default. Configure `OPENROUTER_API_KEY`, `CHAT_ENABLED=true` and optionally `CHAT_MODEL` as server-side environment variables. On the hosted service, use the existing private systemd EnvironmentFile `/etc/last-light-chat.env`; never place a key in chat, GitHub, a VITE variable, dist or a shell command. Python does not automatically load `.env` files. Without activation, guide help, offline mission preparation and real backend calculations still work.

The default origin list includes the production origin, the port-8000 local launcher and Vite's port 5173. Deployment configuration includes a rate-limited `/api/chat/prepare` route. Preserve the assistant anchors and existing Freestyle safeguards. Pushing/merging GitHub changes does not deploy the hosted service. Hosted model activation and a real microphone transcription check remain deployment/user-environment steps.

Validation: production build, JavaScript tests, Python suite with available NASA data, native Chrome checks of clarification/review/calculation/autofill/readability, and a real November 18, 2026 API study whose selected option reproduced identical metrics when evaluated at its exact coordinates/time. Provider tests use mocks and spend no credits.
