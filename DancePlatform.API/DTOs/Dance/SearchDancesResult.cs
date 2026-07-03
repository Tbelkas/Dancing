namespace DancePlatform.API.DTOs.Dance;

public class SearchDancesResult
{
    public List<DanceDto> Items { get; set; } = new();
    public int Total { get; set; }

    /// <summary>Catalog size ignoring filters, for "N of M dances" display.</summary>
    public int GrandTotal { get; set; }
    public int Page { get; set; }
    public int PageSize { get; set; }
}
