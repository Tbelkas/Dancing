namespace DancePlatform.API.DTOs.User;

public class MyStyleWithDancesDto
{
    public int StyleId { get; set; }
    public string StyleName { get; set; } = string.Empty;
    public List<MyDanceItemDto> Dances { get; set; } = new();
}

public class MyDanceItemDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Slug { get; set; } = string.Empty;
    public string Status { get; set; } = string.Empty; // "learned" | "inProgress"
}
