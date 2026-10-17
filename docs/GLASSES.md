# Smart glasses: what the adapter needs, and what is unknown until there's hardware

**Status: not tested on glasses.** Praxis v0 runs on recorded first-person video. Its live mode
(`praxis.live`) was run in real time on a recorded clip replayed at wall-clock speed (`ReplaySource`); the webcam
path (`WebcamSource`, e.g. an iPhone via Continuity Camera standing in for a head-mounted view) is the same loop
but was not run in this build. Glasses are one more
input adapter behind the camera-agnostic `FrameSource` interface (`prototype/praxis/io/sources.py`).
`MetaGlassesSource` is a stub that raises `NotImplementedError` on purpose. It stays that way until
a live stream has run end to end on real hardware.

Sources: Meta's Wearables Device Access Toolkit (DAT) READMEs, changelogs and docs, read 2026-10-17 (links
at the bottom). Nothing below was measured by us.

## How a third-party app gets camera frames from Meta glasses (as documented)

- **SDK.** Meta Wearables Device Access Toolkit (DAT).
  - iOS: Swift package `facebook/meta-wearables-dat-ios`, v1.0.1, 2026-10-09.
  - Android: Maven artifacts `com.meta.wearable:mwdat-*`, also 1.0.1.
  - 1.0.0 shipped 2026-09-24 and Meta announced it as stable at Connect. The GitHub READMEs still say
    "developer preview".
- **Topology.** The glasses pair with the Meta AI app. *Our own phone app* then registers through a deeplink.
  The wearer grants camera permission inside the Meta AI app (allow always / once / deny). Our app then
  opens a camera *session*. **No custom code runs on the glasses.** Our logic runs on the phone, or on a
  server/laptop the phone forwards to.
- **Supported devices** (per docs): Ray-Ban Meta (Gen 1/2), Oakley Meta HSTN / Vanguard, Meta Ray-Ban Display.
- **Distribution.** Public App Store publishing is **not supported yet** (the SDK uses `ExternalAccessory`).
  Builds reach test users through release channels in the Wearables Developer Center. That is fine for a
  pilot; it is not a consumer launch path yet.

## Stream limits (documented, not measured)

| Property | Documented value | Why it matters for Praxis |
|---|---|---|
| Resolution | 720×1280, 504×896, 360×640 (portrait) | Our fast layers already run at 640 px max side; 504×896 is enough. ROI crops for fine checks want the highest tier. |
| Frame rate | 2 / 7 / 15 / 24 / 30 fps | Fast layers run at 4 fps today; 7 fps covers them. Point tracking (TAPNext++) wants ≥15 fps. |
| Codec | raw (pauses when the iOS app is backgrounded) or HEVC `hvc1` (keeps streaming in background) | A coaching app must keep running in the background → HEVC, which adds decode cost on the phone. |
| Bandwidth adaptation | Ladder drops resolution, then fps, "never below 15 fps" | Auto quality changes mid-session; the engine must not assume a fixed resolution (ours doesn't). |
| Transport | Docs say both "constrained by Bluetooth Classic" and "Wi-Fi is added for … camera streaming" | **Unknown which one limits the stream in practice.** |
| Latency | **No official figure** | Biggest unknown. It adds directly to our feedback latency. |
| Photo capture | Frame grab during a stream; standalone photo (beta) up to 4032×3024 | A high-res still on demand would be ideal for the slow-path verifier ("zoom in on the bracket"). Photo and stream can't use the camera at once. |
| Audio out | A2DP stereo; HFP mic (8 kHz mono) disables A2DP | Voice-first coaching uses the speakers; using the mic for voice commands degrades output audio. |
| Display | Meta Ray-Ban Display only: 600×600 declarative UI sent from the phone | Our user-view HUD maps to it (progress, one short card). On other models Praxis is voice-only. |

## What the adapter (`MetaGlassesSource`) needs

1. **Phone companion app** (Swift, DAT): register, request camera permission, open a session at
   `medium` (504×896) and 7–15 fps, HEVC.
2. **Forwarding.** Decode on the phone, then send JPEG frames with capture timestamps over a local socket to
   the Praxis engine on a laptop/server (or run the fast layers on the phone later).
3. **Timestamps.** Use capture time, not arrival time, so time-on-step and feedback latency stay honest.
4. **Back-channel.** Spoken text (TTS on the phone → glasses speakers) and, on the Display model, the
   HUD card as declarative UI.
5. **On-demand stills.** When the policy wants fine evidence, request a photo instead of a stream frame.
   That pauses the stream, so it is a policy decision.
6. **Session lifecycle.** The wearer can pause by tapping, taking the glasses off or closing the hinges.
   The engine must treat that as "no view" (not "no progress").

## Unknown until tested on hardware

- **End-to-end glass-to-phone-to-engine latency.** There is no official number, so this is the first thing we will measure.
- Sustained frame rate and resolution while walking around a workbench, and how often the bandwidth ladder kicks in.
- **Field of view and framing.** Do the glasses see the user's hands and the part during close work (glasses
  sit higher than a head-mounted GoPro; the datasets we evaluated on are GoPro/HoloLens)?
- **Battery and thermal limits** for continuous streaming sessions of 10–30 minutes.
- **Image quality.** Per-frame compression may make fine checks (orientation, screw seated) harder than on dataset video.
- Whether in-stream audio (beta) avoids the HFP/A2DP conflict for voice commands.

## Alternatives (camera access documented)

- **Android XR glasses (Jetpack XR, developer preview).** The phone app gets the glasses camera through
  `ProjectedContext` + CameraX. Google recommends 640×480 @ 10 fps for computer vision.
- **Snap Spectacles (Lens Studio `CameraModule`).** On-device frames. Publishing needs a transparent-permission flow.
- **Brilliant Labs Frame / Halo.** Stills only over BLE (≤720 px / 640 px). Not suitable for continuous tracking.

## Links
- https://github.com/facebook/meta-wearables-dat-ios · https://github.com/facebook/meta-wearables-dat-android
- https://wearables.developer.meta.com/llms.txt?full=true · https://developers.meta.com/wearables/faq/
- https://developers.meta.com/blog/meta-connect-recap-ai-glasses/
- https://developer.android.com/develop/xr/jetpack-xr-sdk/access-hardware-projected-context
- https://developers.snap.com/spectacles/about-spectacles-features/apis/camera-module
- https://docs.brilliant.xyz/frame/frame-sdk-lua/ · https://docs.brilliant.xyz/halo/halo-sdk-lua/
