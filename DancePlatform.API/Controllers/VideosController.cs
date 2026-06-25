using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class VideosController : AppControllerBase
{
    private readonly IVideoService _videoService;
    private readonly IUserVideoLoopService _loopService;

    public VideosController(IVideoService videoService, IUserVideoLoopService loopService)
    {
        _videoService = videoService;
        _loopService = loopService;
    }

    [HttpGet("dance/{danceId}")]
    public async Task<IActionResult> GetByDance(int danceId) =>
        Ok(await _videoService.GetByDanceAsync(danceId, CurrentUserId));

    [HttpGet("{id}/related")]
    public async Task<IActionResult> GetRelated(int id) =>
        Ok(await _videoService.GetRelatedAsync(id));

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var video = await _videoService.GetByIdAsync(id, CurrentUserId);
        return video is null ? NotFound() : Ok(video);
    }

    [Authorize]
    [HttpPost("{id}/rate")]
    public async Task<IActionResult> Rate(int id, [FromBody] RateVideoRequest request)
    {
        var video = await _videoService.RateVideoAsync(CurrentUserId!.Value, id, request.Rating);
        return video is null ? NotFound() : Ok(video);
    }

    [HttpPost("{id}/view")]
    public async Task<IActionResult> IncrementView(int id)
    {
        var ok = await _videoService.IncrementViewCountAsync(id);
        return ok ? NoContent() : NotFound();
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateVideoRequest request)
    {
        var video = await _videoService.CreateAsync(request, CurrentUserId);
        if (video is null) return BadRequest(new { message = "Dance not found." });
        return CreatedAtAction(nameof(GetById), new { id = video.Id }, video);
    }

    [RequireAdmin]
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateVideoRequest request)
    {
        var video = await _videoService.UpdateAsync(id, request, CurrentUserId);
        return video is null ? NotFound() : Ok(video);
    }

    [RequireAdmin]
    [HttpPut("{id}/dance")]
    public async Task<IActionResult> MoveToDance(int id, [FromBody] MoveVideoRequest request)
    {
        var (result, video) = await _videoService.MoveToDanceAsync(id, request.DanceId, CurrentUserId);
        return result switch
        {
            MoveVideoResult.VideoNotFound => NotFound(),
            MoveVideoResult.DanceNotFound => BadRequest(new { message = "Target dance not found." }),
            _ => Ok(video)
        };
    }

    [RequireAdmin]
    [HttpPost("{id}/segments")]
    public async Task<IActionResult> AddSegment(int id, [FromBody] VideoSegmentDto segment)
    {
        var video = await _videoService.AddSegmentAsync(id, segment, CurrentUserId);
        return video is null ? NotFound() : Ok(video);
    }

    [RequireAdmin]
    [HttpDelete("{id}/segments/{segmentId}")]
    public async Task<IActionResult> DeleteSegment(int id, int segmentId)
    {
        var video = await _videoService.DeleteSegmentAsync(id, segmentId, CurrentUserId);
        return video is null ? NotFound() : Ok(video);
    }

    [RequireAdmin]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _videoService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }

    // --- Personal loops: any authenticated user saves loops for their own account ---

    [Authorize]
    [HttpGet("{id}/loops")]
    public async Task<IActionResult> GetMyLoops(int id) =>
        Ok(await _loopService.GetForVideoAsync(CurrentUserId!.Value, id));

    [Authorize]
    [HttpPost("{id}/loops")]
    public async Task<IActionResult> AddMyLoop(int id, [FromBody] VideoSegmentDto loop)
    {
        var loops = await _loopService.AddAsync(CurrentUserId!.Value, id, loop);
        return loops is null ? BadRequest(new { message = "Invalid loop or video not found." }) : Ok(loops);
    }

    [Authorize]
    [HttpDelete("{id}/loops/{loopId}")]
    public async Task<IActionResult> DeleteMyLoop(int id, int loopId)
    {
        var loops = await _loopService.DeleteAsync(CurrentUserId!.Value, id, loopId);
        return loops is null ? NotFound() : Ok(loops);
    }
}
