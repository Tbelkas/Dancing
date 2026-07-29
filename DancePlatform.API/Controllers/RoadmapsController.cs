using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RoadmapsController : AppControllerBase
{
    private readonly IRoadmapService _roadmapService;

    public RoadmapsController(IRoadmapService roadmapService) => _roadmapService = roadmapService;

    // Anonymous callers get the path with zeroed progress; signed-in ones get their own counts,
    // so this must not be response-cached the way the style catalog is.
    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _roadmapService.GetAllAsync(CurrentUserId));

    [HttpGet("{idOrSlug}")]
    public async Task<IActionResult> GetByIdOrSlug(string idOrSlug)
    {
        var roadmap = await _roadmapService.GetByIdOrSlugAsync(idOrSlug, CurrentUserId);
        return roadmap is null ? NotFound() : Ok(roadmap);
    }
}
