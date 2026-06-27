using System.Security.Claims;
using DancePlatform.API.DTOs.Style;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class StylesController : ControllerBase
{
    private readonly IStyleService _styleService;

    public StylesController(IStyleService styleService) => _styleService = styleService;

    private int? CurrentUserId =>
        User.FindFirstValue(ClaimTypes.NameIdentifier) is string id ? int.Parse(id) : null;

    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _styleService.GetAllAsync());

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var style = await _styleService.GetByIdAsync(id);
        return style is null ? NotFound() : Ok(style);
    }

    // Any signed-in user can add a style from the "My Dances" self-service flow
    // (same access level as POST /dances and POST /videos).
    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateStyleRequest request)
    {
        var style = await _styleService.CreateAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = style.Id }, style);
    }

    [RequireAdmin]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _styleService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }

    [Authorize]
    [HttpPost("{id}/mystyle")]
    public async Task<IActionResult> ToggleMyStyle(int id)
    {
        var isMyStyle = await _styleService.ToggleMyStyleAsync(CurrentUserId!.Value, id);
        return Ok(new { isMyStyle });
    }
}
