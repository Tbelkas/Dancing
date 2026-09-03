using DancePlatform.API.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Controllers;

/// <summary>
/// Something to point a monitor at. Anonymous and deliberately thin: it reports whether the API
/// is up and whether it can reach its database, and nothing that would be worth harvesting —
/// no versions, no configuration, no counts.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class HealthController : ControllerBase
{
    private readonly AppDbContext _db;

    public HealthController(AppDbContext db) => _db = db;

    [HttpGet]
    public async Task<IActionResult> Get(CancellationToken ct)
    {
        // An API that answers while its database is unreachable is exactly the state worth
        // paging about, so the check has to touch the database rather than just return 200.
        bool database;
        try
        {
            database = await _db.Database.CanConnectAsync(ct);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            database = false;
        }

        var body = new { status = database ? "healthy" : "degraded", database };
        return database ? Ok(body) : StatusCode(StatusCodes.Status503ServiceUnavailable, body);
    }
}
