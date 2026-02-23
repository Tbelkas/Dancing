using System.Security.Claims;
using DancePlatform.API.DTOs.Dance;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class DancesController : ControllerBase
{
    private readonly IDanceService _danceService;

    public DancesController(IDanceService danceService) => _danceService = danceService;

    private int? CurrentUserId =>
        User.FindFirstValue(ClaimTypes.NameIdentifier) is string id ? int.Parse(id) : null;

    [HttpGet]
    public async Task<IActionResult> GetAll() =>
        Ok(await _danceService.GetAllAsync(CurrentUserId));

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var dance = await _danceService.GetByIdAsync(id, CurrentUserId);
        return dance is null ? NotFound() : Ok(dance);
    }

    [Authorize]
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateDanceRequest request)
    {
        var dance = await _danceService.CreateAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = dance.Id }, dance);
    }

    [Authorize]
    [HttpPut("{id}")]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateDanceRequest request)
    {
        var dance = await _danceService.UpdateAsync(id, request);
        return dance is null ? NotFound() : Ok(dance);
    }

    [Authorize]
    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _danceService.DeleteAsync(id);
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
    [HttpPost("{id}/learned")]
    public async Task<IActionResult> ToggleLearned(int id)
    {
        var isLearned = await _danceService.ToggleLearnedAsync(CurrentUserId!.Value, id);
        return Ok(new { isLearned });
    }
}
