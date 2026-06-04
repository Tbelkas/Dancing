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
}
