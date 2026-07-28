# Module — Videos & Player (clips, segments, embeds)

> Load alongside core-context.md for anything touching video data or the player.

## Backend
- Controller: `Controllers/VideosController.cs`
- Service: `IVideoService` / `VideoService.cs`
- Models: `Video` (FK → Dance), `VideoSegment` (FK → Video, **cascade delete**)
- DTOs: `DTOs/Video/` — `VideoDto`, `VideoSegmentDto`, `CreateVideoRequest`, `UpdateVideoRequest`
- Endpoints (api-contracts → Videos): get-by-dance, get-one, `POST /videos/{id}/view`
  (anonymous view-count bump), create (⚠️ currently unauthenticated), admin update/delete.

## Chapter suggestions (adding a YouTube clip)
- `IYoutubeChapterService` / `YoutubeChapterService.cs` reads a video's own chapters off its
  watch page (`GET /videos/youtube/{videoId}/chapters`, admin-only, cached 6h / 30min on a miss).
  Two sources: YouTube's chapter bar (`chapterRenderer` in the embedded JSON), else the
  description's timestamp list. It's scraping, so it's best-effort by design — every failure
  path returns an empty list, and the add form still takes sections by hand.
- Both add-video forms (`shared/components/add-video-form`, `pages/admin-add-video`) fetch on
  URL paste and *offer* the chapters as chips; the admin applies them with a click. Applying
  sets `videoType = 'tutorial'` — `VideoService.MapSegments` drops segments on any other type.

## Frontend
- Component: `shared/components/video-player/` (reusable; used on dance detail)
- Pipe: `shared/pipes/trust-url.pipe.ts` (`TrustUrl` — sanitizes/embeds iframe src; required
  for Angular to allow the embed URL)
- Service: `core/services/video.service.ts`; Model: `models/video.model.ts`

## Camera pane (practise against yourself)
- `shared/components/camera-pane/` + `core/services/camera.service.ts`. Entirely browser-local:
  no endpoint, no upload, nothing persisted but preferences in localStorage (`dp_camera_*`).
- Lives **inside** each player's `.player-media` frame so it fullscreens with the video. Side
  mode splits that frame into two grid columns; overlay mode lifts the pane out of the flow and
  ghosts it over the video at an adjustable blend.
- **The stream is a singleton.** Dance detail can mount several players at once; one *owns* the
  camera at a time (`CameraService.owner`), and every player's `ngOnDestroy` calls
  `camera.release(this)` — a stream left running keeps the camera light on after navigation.
- **Delayed replay** records `delaySeconds`-long clips and loops the finished one while the next
  records. A continuous N-second-behind feed isn't achievable on the web: MediaRecorder chunks
  can't be played independently, and a frame ring buffer costs tens of MB per few seconds.
- Wire recorder callbacks with `addEventListener`, never `recorder.onstop = …` — zone.js patches
  the former, so the latter updates the picture without updating the UI around it.
- Needs a secure context (https, or localhost in dev); `CameraService.unsupportedReason` states
  why when there isn't one, and a failed start keeps the pane mounted to explain itself.

## Data shape / behaviour
- `Platform` (default `"youtube"`; also tiktok, instagram), `VideoType` (default `"steps"`),
  `VideoId` = the platform embed id.
- **Clip bounds:** `StartTime`/`EndTime` (seconds, nullable) bound the playable range.
- **Segments:** named sub-ranges (`Label`, `StartTime`, optional `EndTime`) powering the
  repeat-region / labelled-section feature. Deleting a video cascades its segments.
- Player supports speed adjustment and repeat-region (per product spec).

## Gotchas
- Third-party embeds (TikTok/YouTube) spam the console — **won't fix**, out of our control
  (known-issues #6). Don't chase those errors.
- Always render embed URLs through `TrustUrl`; raw binding will be stripped by Angular.
