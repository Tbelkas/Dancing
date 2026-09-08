using System.ComponentModel.DataAnnotations;

namespace DancePlatform.API.DTOs.Admin;

/// <summary>Both tag vocabularies with their usage, for the tag manager.</summary>
public class TagAdminDto
{
    public List<TagUsageDto> Styles { get; set; } = new();
    public List<TagUsageDto> MusicalStyles { get; set; } = new();
}

public class TagUsageDto
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    /// <summary>What this name slugifies to — for a style, that's the {style} segment of every dance URL under it.</summary>
    public string Slug { get; set; } = string.Empty;
    public string? Description { get; set; }
    /// <summary>Dances carrying this tag. Zero means nothing links to it at all.</summary>
    public int DanceCount { get; set; }
}

public class RenameTagRequest
{
    [Required, MinLength(2), MaxLength(80)] public string Name { get; set; } = string.Empty;
}

public class MergeTagRequest
{
    /// <summary>The tag to keep. Every dance on the source moves here, then the source is deleted.</summary>
    [Required] public int TargetId { get; set; }
}

/// <summary>What a merge actually did — the numbers are the only way to check it did what you meant.</summary>
public class MergeTagResultDto
{
    public string SourceName { get; set; } = string.Empty;
    public string TargetName { get; set; } = string.Empty;
    /// <summary>Dances moved onto the target.</summary>
    public int Moved { get; set; }
    /// <summary>Dances that already carried both tags, so the source link was simply dropped.</summary>
    public int AlreadyTagged { get; set; }
    /// <summary>Slugs rewritten afterwards — merging two styles can collide slugs inside the survivor.</summary>
    public int Reslugged { get; set; }
}
