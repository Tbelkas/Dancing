namespace DancePlatform.API.DTOs.Dance;

public class SearchDancesResult
{
    public List<DanceDto> Items { get; set; } = new();
    public int Total { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
}
