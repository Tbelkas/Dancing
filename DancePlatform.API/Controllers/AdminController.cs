using DancePlatform.API.DTOs.Admin;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

/// <summary>
/// Admin-only surfaces that aren't about one resource. Everything about a dance or a video lives
/// on its own controller; what lands here is the view across all of them.
/// </summary>
[ApiController]
[Route("api/[controller]")]
[RequireAdmin]
public class AdminController : AppControllerBase
{
    private readonly IAdminHealthService _health;
    private readonly ITagAdminService _tags;

    public AdminController(IAdminHealthService health, ITagAdminService tags)
    {
        _health = health;
        _tags = tags;
    }

    /// <summary>
    /// Catalogue health: the headline counts plus every check that used to be a script someone
    /// had to remember to run. Uncached — it is a dozen counts over a sub-thousand-row catalogue,
    /// read by one person a few times a day, and a stale dashboard is worse than a slow one.
    /// </summary>
    [HttpGet("health")]
    public async Task<IActionResult> GetHealth() => Ok(await _health.GetAsync());

    // --- Tags ------------------------------------------------------------
    // {kind} is "style" or "music". Two vocabularies with identical shape and identical
    // operations; separate routes for each would be the same code twice.

    [HttpGet("tags")]
    public async Task<IActionResult> GetTags() => Ok(await _tags.GetAsync());

    [HttpPut("tags/{kind}/{id:int}")]
    public async Task<IActionResult> RenameTag(string kind, int id, [FromBody] RenameTagRequest request)
    {
        var (result, tag) = await _tags.RenameAsync(kind, id, request.Name);
        return result switch
        {
            TagEditResult.NotFound => NotFound(),
            TagEditResult.Duplicate => Conflict(new { message = $"\"{request.Name}\" already exists." }),
            _ => Ok(tag)
        };
    }

    /// <summary>
    /// Folds one tag into another: every dance moves across, then the source is deleted. This is
    /// what was missing when the catalogue accumulated near-duplicate tags — the only previous fix
    /// was SQL.
    /// </summary>
    [HttpPost("tags/{kind}/{id:int}/merge")]
    public async Task<IActionResult> MergeTag(string kind, int id, [FromBody] MergeTagRequest request)
    {
        var (result, merge) = await _tags.MergeAsync(kind, id, request.TargetId);
        return result switch
        {
            TagEditResult.NotFound => NotFound(),
            TagEditResult.SameTag => BadRequest(new { message = "A tag can't be merged into itself." }),
            _ => Ok(merge)
        };
    }

    [HttpDelete("tags/{kind}/{id:int}")]
    public async Task<IActionResult> DeleteTag(string kind, int id)
    {
        var result = await _tags.DeleteAsync(kind, id);
        return result switch
        {
            TagEditResult.NotFound => NotFound(),
            // Deleting a tag that's in use would silently untag every dance under it. Merge instead.
            TagEditResult.InUse => Conflict(new { message = "That tag is still on some dances. Merge it into another one instead." }),
            _ => NoContent()
        };
    }
}
