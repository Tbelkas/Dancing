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

    // Catalog-level data that only changes on seeding/admin edits — let browsers reuse it briefly.
    // No longer publicly cacheable: the list now includes the caller's own dances awaiting
    // review, so a shared cache entry would hand one user another user's pending entries.
    [HttpGet("names")]
    [ResponseCache(Duration = 300, Location = ResponseCacheLocation.Client, VaryByHeader = "Authorization")]
    public async Task<IActionResult> GetNames() =>
        Ok(await _danceService.GetNamesAsync(CurrentUserId, CurrentUserIsAdmin));

    [HttpGet("{idOrSlug}")]
    public async Task<IActionResult> GetByIdOrSlug(string idOrSlug)
    {
        var dance = int.TryParse(idOrSlug, out var id)
            ? await _danceService.GetByIdAsync(id, CurrentUserId, CurrentUserIsAdmin)
            : await _danceService.GetBySlugAsync(idOrSlug, CurrentUserId, CurrentUserIsAdmin);
        return dance is null ? NotFound() : Ok(dance);
    }

    [HttpGet("{styleSlug}/{danceSlug}")]
    public async Task<IActionResult> GetByStyleAndSlug(string styleSlug, string danceSlug)
    {
        var dance = await _danceService.GetByStyleAndSlugAsync(styleSlug, danceSlug, CurrentUserId, CurrentUserIsAdmin);
        return dance is null ? NotFound() : Ok(dance);
    }

    [HttpGet("{id:int}/recommended")]
    public async Task<IActionResult> GetRecommended(int id) =>
        Ok(await _danceService.GetRecommendedAsync(id, CurrentUserId));

    // Server-side prev/next pager for the dance-detail page — replaces the client fetching up to
    // 500 dances just to locate two neighbours. Anonymous, like GetRecommended; the viewer's flags
    // still populate via CurrentUserId. Always 200 with {prev, next} (either may be null at an edge).
    [HttpGet("{id:int}/neighbors")]
    public async Task<IActionResult> GetNeighbors(int id) =>
        Ok(await _danceService.GetNeighborsAsync(id, CurrentUserId));

    /// <summary>One-time maintenance: recompute slugs under the per-style uniqueness rule.</summary>
    [RequireAdmin]
    [HttpPost("reslug")]
    public async Task<IActionResult> Reslug() =>
        Ok(new { changed = await _danceService.ReslugAllAsync() });

    /// <summary>
    /// Deliberately [Authorize] and not [RequireAdmin] — the My Dances page is a self-service add
    /// flow (see known-issues A). What keeps that from being an open door onto the public catalogue
    /// is that a non-admin's dance is created "pending": theirs to see and to hang a video on,
    /// invisible to everyone else until it is approved.
    /// </summary>
    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateDanceRequest request)
    {
        var (result, dance) = await _danceService.CreateAsync(request, CurrentUserId, CurrentUserIsAdmin);
        if (result == CreateDanceResult.DuplicateName)
            return Conflict(new { message = $"\"{request.Name}\" already exists in that style.", dance });
        return CreatedAtAction(nameof(GetByIdOrSlug), new { idOrSlug = dance!.Id }, dance);
    }

    /// <summary>The review queue: user-added dances not yet in the public catalogue.</summary>
    [RequireAdmin]
    [HttpGet("pending")]
    public async Task<IActionResult> GetPending() =>
        Ok(await _danceService.GetPendingAsync());

    [RequireAdmin]
    [HttpPost("{id}/review")]
    public async Task<IActionResult> Review(int id, [FromBody] ReviewDanceRequest request)
    {
        var dance = await _danceService.SetReviewStateAsync(id, request.ReviewState);
        return dance is null ? NotFound() : Ok(dance);
    }

    [RequireAdmin]
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateDanceRequest request)
    {
        var dance = await _danceService.UpdateAsync(id, request);
        return dance is null ? NotFound() : Ok(dance);
    }

    /// <summary>[Authorize], not [RequireAdmin]: the service decides. An admin may delete any
    /// dance; a contributor may withdraw their own while it is still awaiting review.</summary>
    [Authorize]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _danceService.DeleteAsync(id, CurrentUserId, CurrentUserIsAdmin);
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
    [HttpPut("{id}/status")]
    public async Task<IActionResult> SetStatus(int id, [FromBody] SetStatusRequest request)
    {
        var result = await _danceService.SetStatusAsync(CurrentUserId!.Value, id, request.Status);
        return Ok(result);
    }

}
