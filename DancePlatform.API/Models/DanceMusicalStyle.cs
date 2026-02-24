namespace DancePlatform.API.Models;

public class DanceMusicalStyle
{
    public int DanceId { get; set; }
    public Dance Dance { get; set; } = null!;

    public int MusicalStyleId { get; set; }
    public MusicalStyle MusicalStyle { get; set; } = null!;
}
