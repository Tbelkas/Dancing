using DancePlatform.API.DTOs.Glossary;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

/// <summary>
/// Reading a glossary is public; anonymous callers get every term unlearned. Not response-cached:
/// the payload carries the caller's own learned marks.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class GlossaryController : AppControllerBase
{
    private readonly IGlossaryService _glossaryService;

    public GlossaryController(IGlossaryService glossaryService) => _glossaryService = glossaryService;

    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _glossaryService.GetAllAsync(CurrentUserId));

    [HttpGet("{styleSlug}")]
    public async Task<IActionResult> GetByStyle(string styleSlug)
    {
        var glossary = await _glossaryService.GetByStyleAsync(styleSlug, CurrentUserId);
        return glossary is null ? NotFound() : Ok(glossary);
    }

    /// <summary>Sets rather than toggles, so a retried request can't flip the mark back.</summary>
    [HttpPut("terms/{id:int}/learned")]
    [Authorize]
    public async Task<IActionResult> SetLearned(int id, [FromBody] SetGlossaryLearnedRequest request) =>
        await _glossaryService.SetLearnedAsync(CurrentUserId!.Value, id, request.Learned) ? NoContent() : NotFound();
}
