using DancePlatform.API.DTOs.Import;
using DancePlatform.API.Filters;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ImportController : ControllerBase
{
    private readonly IImportService _importService;

    public ImportController(IImportService importService) => _importService = importService;

    [RequireAdmin]
    [HttpPost("dances")]
    public async Task<IActionResult> ImportDances([FromBody] BulkImportRequest request)
    {
        var result = await _importService.ImportDancesAsync(request);
        return Ok(result);
    }

    [RequireAdmin]
    [HttpPost("youtube-video")]
    public async Task<IActionResult> ImportYoutubeVideo([FromBody] YoutubeVideoImportRequest request)
    {
        var (result, video) = await _importService.ImportYoutubeVideoAsync(request);
        return result switch
        {
            ImportVideoResult.InvalidUrl => BadRequest(new { message = "Invalid YouTube URL." }),
            ImportVideoResult.DanceNotFound => BadRequest(new { message = "Dance not found." }),
            ImportVideoResult.Duplicate => Conflict(new { message = "This video is already on this dance." }),
            _ => Ok(video)
        };
    }
}
