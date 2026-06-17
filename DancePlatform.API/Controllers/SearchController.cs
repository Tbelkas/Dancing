using System.Security.Claims;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class SearchController : ControllerBase
{
    private readonly IDanceService _danceService;

    public SearchController(IDanceService danceService) => _danceService = danceService;

    private int? CurrentUserId =>
        User.FindFirstValue(ClaimTypes.NameIdentifier) is string id ? int.Parse(id) : null;

    [HttpGet("dances")]
    public async Task<IActionResult> SearchDances(
        [FromQuery] string? q,
        [FromQuery] int? styleId,
        [FromQuery] int? musicalStyleId,
        [FromQuery] string? difficulty,
        [FromQuery] string? status,
        [FromQuery] string? sortBy,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 24)
    {
        var clamped = Math.Min(Math.Max(pageSize, 1), 100);
        var result = await _danceService.SearchAsync(q ?? string.Empty, styleId, musicalStyleId, difficulty, status, sortBy, CurrentUserId, page, clamped);
        return Ok(result);
    }
}
