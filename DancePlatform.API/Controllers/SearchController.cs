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
    public async Task<IActionResult> SearchDances([FromQuery] string? q, [FromQuery] int? styleId)
    {
        var results = await _danceService.SearchAsync(q ?? string.Empty, styleId, CurrentUserId);
        return Ok(results);
    }
}
