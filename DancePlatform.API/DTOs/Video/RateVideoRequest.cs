using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Video;

public class RateVideoRequest
{
    [Required, Range(1, 5)] public int Rating { get; set; }
}
