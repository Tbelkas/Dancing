using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class SearchController : AppControllerBase
{
    private readonly IDanceService _danceService;

    public SearchController(IDanceService danceService) => _danceService = danceService;

    [HttpGet("dances")]
    public async Task<IActionResult> SearchDances(
        [FromQuery] string? q,
        [FromQuery] int? styleId,
        [FromQuery] int? musicalStyleId,
        [FromQuery] string? difficulty,
        [FromQuery] string? status,
        [FromQuery] string? sortBy,
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = 24,
        [FromQuery] bool favoritesOnly = false)
    {
        var clamped = Math.Min(Math.Max(pageSize, 1), 100);
        var result = await _danceService.SearchAsync(q ?? string.Empty, styleId, musicalStyleId, difficulty, status, sortBy, CurrentUserId, page, clamped, favoritesOnly);
        return Ok(result);
    }

    [HttpGet("dances/random")]
    public async Task<IActionResult> RandomDance(
        [FromQuery] string? q,
        [FromQuery] int? styleId,
        [FromQuery] int? musicalStyleId,
        [FromQuery] string? difficulty,
        [FromQuery] string? status,
        [FromQuery] bool favoritesOnly = false)
    {
        var dance = await _danceService.RandomAsync(q ?? string.Empty, styleId, musicalStyleId, difficulty, status, CurrentUserId, favoritesOnly);
        return dance is null ? NotFound(new { message = "No dances match the filters." }) : Ok(dance);
    }
}
