using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DancesController : AppControllerBase
{
    private readonly IDanceService _danceService;

    public DancesController(IDanceService danceService) => _danceService = danceService;

    [HttpGet("names")]
    public async Task<IActionResult> GetNames() =>
        Ok(await _danceService.GetNamesAsync());

    [HttpGet("{idOrSlug}")]
    public async Task<IActionResult> GetByIdOrSlug(string idOrSlug)
    {
        var dance = int.TryParse(idOrSlug, out var id)
            ? await _danceService.GetByIdAsync(id, CurrentUserId)
            : await _danceService.GetBySlugAsync(idOrSlug, CurrentUserId);
        return dance is null ? NotFound() : Ok(dance);
    }

    [HttpGet("{styleSlug}/{danceSlug}")]
    public async Task<IActionResult> GetByStyleAndSlug(string styleSlug, string danceSlug)
    {
        var dance = await _danceService.GetByStyleAndSlugAsync(styleSlug, danceSlug, CurrentUserId);
        return dance is null ? NotFound() : Ok(dance);
    }

    [HttpGet("{id:int}/recommended")]
    public async Task<IActionResult> GetRecommended(int id) =>
        Ok(await _danceService.GetRecommendedAsync(id, CurrentUserId));

    /// <summary>One-time maintenance: recompute slugs under the per-style uniqueness rule.</summary>
    [RequireAdmin]
    [HttpPost("reslug")]
    public async Task<IActionResult> Reslug() =>
        Ok(new { changed = await _danceService.ReslugAllAsync() });

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateDanceRequest request)
    {
        var dance = await _danceService.CreateAsync(request);
        return CreatedAtAction(nameof(GetByIdOrSlug), new { idOrSlug = dance.Id }, dance);
    }

    [RequireAdmin]
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateDanceRequest request)
    {
        var dance = await _danceService.UpdateAsync(id, request);
        return dance is null ? NotFound() : Ok(dance);
    }

    [RequireAdmin]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _danceService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }

    [Authorize]
    [HttpPost("{id}/favorite")]
    public async Task<IActionResult> ToggleFavorite(int id)
    {
        var isFavorite = await _danceService.ToggleFavoriteAsync(CurrentUserId!.Value, id);
        return Ok(new { isFavorite });
    }

    [Authorize]
    [HttpPost("{id}/learned")]
    public async Task<IActionResult> ToggleLearned(int id)
    {
        var isLearned = await _danceService.ToggleLearnedAsync(CurrentUserId!.Value, id);
        return Ok(new { isLearned });
    }

    [Authorize]
    [HttpPost("{id}/inprogress")]
    public async Task<IActionResult> ToggleInProgress(int id)
    {
        var isInProgress = await _danceService.ToggleInProgressAsync(CurrentUserId!.Value, id);
        return Ok(new { isInProgress });
    }

    [Authorize]
    [HttpPut("{id}/status")]
    public async Task<IActionResult> SetStatus(int id, [FromBody] SetStatusRequest request)
    {
        var result = await _danceService.SetStatusAsync(CurrentUserId!.Value, id, request.Status);
        return Ok(result);
    }

}
