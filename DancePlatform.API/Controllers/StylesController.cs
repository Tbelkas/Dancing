using DancePlatform.API.DTOs.Style;
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

    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _styleService.GetAllAsync());

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var style = await _styleService.GetByIdAsync(id);
        return style is null ? NotFound() : Ok(style);
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateStyleRequest request)
    {
        var style = await _styleService.CreateAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = style.Id }, style);
    }

    [Authorize]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _styleService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }
}
