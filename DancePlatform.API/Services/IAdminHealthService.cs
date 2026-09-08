using DancePlatform.API.DTOs.Admin;

namespace DancePlatform.API.Services;

/// <summary>
/// The catalogue's standing health, computed on demand.
///
/// Every check here already existed as a script somebody had to remember to run — audit_labels,
/// chip_health, verify_intake, backfill_durations. The point of gathering them is that nobody has
/// to remember, and that each finding links straight to the page where it gets fixed.
/// </summary>
public interface IAdminHealthService
{
    Task<CatalogHealthDto> GetAsync();
}
