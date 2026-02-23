namespace DancePlatform.API.Models;

public class DanceStyle
{
    public int DanceId { get; set; }
    public Dance Dance { get; set; } = null!;

    public int StyleId { get; set; }
    public Style Style { get; set; } = null!;
}
