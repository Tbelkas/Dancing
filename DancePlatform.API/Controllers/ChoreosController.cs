using DancePlatform.API.DTOs.Choreo;
using DancePlatform.API.DTOs.Video;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

/// <summary>
/// Local choreo videos: only the file's name and the user's saved time slots live on
/// the server — playback happens straight from the user's disk in the browser.
/// Everything here is scoped to the signed-in user; there is no admin or public view.
/// </summary>
[ApiController]
[Authorize]
[Route("api/[controller]")]
public class ChoreosController : AppControllerBase
{
    private readonly IChoreoService _choreoService;

    public ChoreosController(IChoreoService choreoService) => _choreoService = choreoService;

    [HttpGet]
    public async Task<IActionResult> GetMine() =>
        Ok(await _choreoService.GetMineAsync(CurrentUserId!.Value));

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var choreo = await _choreoService.GetByIdAsync(CurrentUserId!.Value, id);
        return choreo is null ? NotFound() : Ok(choreo);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateChoreoRequest request)
    {
        var choreo = await _choreoService.CreateAsync(CurrentUserId!.Value, request);
        if (choreo is null) return BadRequest(new { message = "Name and file name are required." });
        return CreatedAtAction(nameof(GetById), new { id = choreo.Id }, choreo);
    }

    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateChoreoRequest request)
    {
        var choreo = await _choreoService.UpdateAsync(CurrentUserId!.Value, id, request);
        return choreo is null ? NotFound() : Ok(choreo);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id) =>
        await _choreoService.DeleteAsync(CurrentUserId!.Value, id) ? NoContent() : NotFound();

    [HttpPost("{id}/loops")]
    public async Task<IActionResult> AddLoop(int id, [FromBody] VideoSegmentDto loop)
    {
        var choreo = await _choreoService.AddLoopAsync(CurrentUserId!.Value, id, loop);
        return choreo is null ? BadRequest(new { message = "Invalid loop or choreo not found." }) : Ok(choreo);
    }

    [HttpDelete("{id}/loops/{loopId}")]
    public async Task<IActionResult> DeleteLoop(int id, int loopId)
    {
        var choreo = await _choreoService.DeleteLoopAsync(CurrentUserId!.Value, id, loopId);
        return choreo is null ? NotFound() : Ok(choreo);
    }
}
