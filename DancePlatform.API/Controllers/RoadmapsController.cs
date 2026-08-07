using DancePlatform.API.DTOs.Roadmap;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

/// <summary>
/// Reading a path is public; building one is not. The two GETs serve the curated paths to anyone
/// and add the caller's own skill trees on top; everything below them is scoped to the signed-in
/// user by the service, which treats another user's tree as not existing rather than forbidden.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class RoadmapsController : AppControllerBase
{
    private readonly IRoadmapService _roadmapService;

    public RoadmapsController(IRoadmapService roadmapService) => _roadmapService = roadmapService;

    // Anonymous callers get the curated paths with zeroed progress; signed-in ones get their own
    // counts and their own trees, so this must not be response-cached the way the style catalog is.
    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _roadmapService.GetAllAsync(CurrentUserId));

    [HttpGet("{idOrSlug}")]
    public async Task<IActionResult> GetByIdOrSlug(string idOrSlug)
    {
        var roadmap = await _roadmapService.GetByIdOrSlugAsync(idOrSlug, CurrentUserId);
        return roadmap is null ? NotFound() : Ok(roadmap);
    }

    [HttpPost]
    [Authorize]
    public async Task<IActionResult> Create([FromBody] SaveRoadmapRequest request)
    {
        var result = await _roadmapService.CreateAsync(CurrentUserId!.Value, request);
        return result.Roadmap is null
            ? Failure(result)
            : CreatedAtAction(nameof(GetByIdOrSlug), new { idOrSlug = result.Roadmap.Slug }, result.Roadmap);
    }

    /// <summary>Replaces the whole tree — see <see cref="SaveRoadmapRequest"/>.</summary>
    [HttpPut("{id:int}")]
    [Authorize]
    public async Task<IActionResult> Update(int id, [FromBody] SaveRoadmapRequest request)
    {
        var result = await _roadmapService.UpdateAsync(CurrentUserId!.Value, id, request);
        return result.Roadmap is null ? Failure(result) : Ok(result.Roadmap);
    }

    [HttpDelete("{id:int}")]
    [Authorize]
    public async Task<IActionResult> Delete(int id) =>
        await _roadmapService.DeleteAsync(CurrentUserId!.Value, id) ? NoContent() : NotFound();

    /// <summary>
    /// Shares one of the caller's own trees, or stops sharing it. Separate from the save on
    /// purpose — see <see cref="IRoadmapService.SetSharedAsync"/>.
    /// </summary>
    [HttpPut("{id:int}/share")]
    [Authorize]
    public async Task<IActionResult> SetShared(int id, [FromBody] SetRoadmapSharedRequest request)
    {
        var roadmap = await _roadmapService.SetSharedAsync(CurrentUserId!.Value, id, request.Shared);
        return roadmap is null ? NotFound() : Ok(roadmap);
    }

    /// <summary>
    /// Forks any path the caller can read into a tree of their own. The way to personalise a
    /// curated path: the curated one stays untouched, and the copy is theirs to cut about.
    /// </summary>
    [HttpPost("{idOrSlug}/copy")]
    [Authorize]
    public async Task<IActionResult> Copy(string idOrSlug)
    {
        var result = await _roadmapService.CopyAsync(CurrentUserId!.Value, idOrSlug);
        return result.Roadmap is null
            ? Failure(result)
            : CreatedAtAction(nameof(GetByIdOrSlug), new { idOrSlug = result.Roadmap.Slug }, result.Roadmap);
    }

    /// <summary>
    /// A failed save is either something the user can fix (400 with the message to show them) or
    /// a tree that isn't theirs (404) — the service tells the two apart by whether it set an error.
    /// </summary>
    private IActionResult Failure(RoadmapSaveResult result) =>
        result.Error is null ? NotFound() : BadRequest(new { message = result.Error });
}
