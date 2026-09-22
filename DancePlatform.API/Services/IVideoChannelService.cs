namespace DancePlatform.API.Services;

/// <summary>Looks up who published a source video: the channel's display name and a link to it.</summary>
public interface IVideoChannelService
{
    /// <summary>Null when the platform has no public lookup or the lookup failed.</summary>
    Task<(string Name, string Url)?> LookupAsync(string platform, string videoId, CancellationToken ct = default);
}
