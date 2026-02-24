using DancePlatform.API.DTOs.MusicalStyle;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class MusicalStylesController : ControllerBase
{
    private readonly IMusicalStyleService _musicalStyleService;

    public MusicalStylesController(IMusicalStyleService musicalStyleService) =>
        _musicalStyleService = musicalStyleService;

    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _musicalStyleService.GetAllAsync());

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var style = await _musicalStyleService.GetByIdAsync(id);
        return style is null ? NotFound() : Ok(style);
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateMusicalStyleRequest request)
    {
        var style = await _musicalStyleService.CreateAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = style.Id }, style);
    }

    [Authorize]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _musicalStyleService.DeleteAsync(id);
        return deleted ? NoContent() : NotFound();
    }
}
