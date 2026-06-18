using DancePlatform.API.DTOs.Practice;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class PracticeController : AppControllerBase
{
    private readonly IPracticeService _practiceService;

    public PracticeController(IPracticeService practiceService) => _practiceService = practiceService;

    [HttpGet]
    public async Task<IActionResult> GetAll() =>
        Ok(await _practiceService.GetAsync(CurrentUserId!.Value));

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreatePracticeSessionRequest request)
    {
        var session = await _practiceService.CreateAsync(CurrentUserId!.Value, request);
        return session is null ? BadRequest(new { message = "Dance not found." }) : Ok(session);
    }

    [HttpDelete("{id}")]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _practiceService.DeleteAsync(CurrentUserId!.Value, id);
        return deleted ? NoContent() : NotFound();
    }
}
