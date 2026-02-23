using DancePlatform.API.DTOs.Video;
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

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var video = await _videoService.GetByIdAsync(id);
        return video is null ? NotFound() : Ok(video);
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateVideoRequest request)
    {
        var video = await _videoService.CreateAsync(request);
        if (video is null) return BadRequest(new { message = "Dance not found." });
        return CreatedAtAction(nameof(GetById), new { id = video.Id }, video);
    }

    [Authorize]
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateVideoRequest request)
    {
        var video = await _videoService.UpdateAsync(id, request);
        return video is null ? NotFound() : Ok(video);
    }

    [Authorize]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _videoService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }
}
