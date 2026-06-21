using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class VideosController : ControllerBase
{
    private readonly IVideoService _videoService;

    public VideosController(IVideoService videoService) => _videoService = videoService;

    [HttpGet("dance/{danceId}")]
    public async Task<IActionResult> GetByDance(int danceId) =>
        Ok(await _videoService.GetByDanceAsync(danceId));

    [HttpGet("{id}/related")]
    public async Task<IActionResult> GetRelated(int id) =>
        Ok(await _videoService.GetRelatedAsync(id));

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var video = await _videoService.GetByIdAsync(id);
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
        var video = await _videoService.CreateAsync(request);
        if (video is null) return BadRequest(new { message = "Dance not found." });
        return CreatedAtAction(nameof(GetById), new { id = video.Id }, video);
    }

    [RequireAdmin]
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateVideoRequest request)
    {
        var video = await _videoService.UpdateAsync(id, request);
        return video is null ? NotFound() : Ok(video);
    }

    [RequireAdmin]
    [HttpPost("{id}/segments")]
    public async Task<IActionResult> AddSegment(int id, [FromBody] VideoSegmentDto segment)
    {
        var video = await _videoService.AddSegmentAsync(id, segment);
        return video is null ? NotFound() : Ok(video);
    }

    [RequireAdmin]
    [HttpDelete("{id}/segments/{segmentId}")]
    public async Task<IActionResult> DeleteSegment(int id, int segmentId)
    {
        var video = await _videoService.DeleteSegmentAsync(id, segmentId);
        return video is null ? NotFound() : Ok(video);
    }

    [RequireAdmin]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _videoService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }
}
