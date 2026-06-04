using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Import;

public class BulkImportRequest
{
    [Required] public string Text { get; set; } = string.Empty;
}
