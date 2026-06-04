using DancePlatform.API.DTOs.Import;

namespace DancePlatform.API.Services;

public interface IImportService
{
    Task<BulkImportResult> ImportDancesAsync(BulkImportRequest request);
}
