using DancePlatform.API.DTOs.Glossary;

namespace DancePlatform.API.Services;

public interface IGlossaryService
{
    /// <summary>Every style that has a glossary, with the caller's progress through it.</summary>
    Task<List<GlossarySummaryDto>> GetAllAsync(int? userId);

    /// <summary>One style's full glossary by style slug, or null when that style has none.</summary>
    Task<GlossaryDto?> GetByStyleAsync(string styleSlug, int? userId);

    /// <summary>
    /// Marks a move learned or not. Idempotent. False when the term doesn't exist or is a concept,
    /// which has nothing to learn.
    /// </summary>
    Task<bool> SetLearnedAsync(int userId, int termId, bool learned);
}
