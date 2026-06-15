using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Dance;

public class SetStatusRequest
{
    /// <summary>The single learning status to set: notstarted, inprogress, or learned.</summary>
    [Required]
    [RegularExpression("^(notstarted|inprogress|learned)$",
        ErrorMessage = "Status must be notstarted, inprogress, or learned.")]
    public string Status { get; set; } = string.Empty;
}
