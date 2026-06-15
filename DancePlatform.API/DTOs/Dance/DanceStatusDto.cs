namespace DancePlatform.API.DTOs.Dance;

/// <summary>The resulting learning status after a SetStatus call. Mutually exclusive by construction.</summary>
public record DanceStatusDto(bool IsLearned, bool IsInProgress);
