using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Dance;

public class RateDanceRequest
{
    [Required, Range(1, 5)] public int Rating { get; set; }
}
