# Module — Videos & Player (clips, segments, embeds)

> Load alongside core-context.md for anything touching video data or the player.

## Backend
- Controller: `Controllers/VideosController.cs`
- Service: `IVideoService` / `VideoService.cs`
- Models: `Video` (FK → Dance), `VideoSegment` (FK → Video, **cascade delete**)
- DTOs: `DTOs/Video/` — `VideoDto`, `VideoSegmentDto`, `CreateVideoRequest`, `UpdateVideoRequest`
- Endpoints (api-contracts → Videos): get-by-dance, get-one, `POST /videos/{id}/view`
  (anonymous view-count bump), create (⚠️ currently unauthenticated), admin update/delete.

## Frontend
- Component: `shared/components/video-player/` (reusable; used on dance detail)
- Pipe: `shared/pipes/trust-url.pipe.ts` (`TrustUrl` — sanitizes/embeds iframe src; required
  for Angular to allow the embed URL)
- Service: `core/services/video.service.ts`; Model: `models/video.model.ts`

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
