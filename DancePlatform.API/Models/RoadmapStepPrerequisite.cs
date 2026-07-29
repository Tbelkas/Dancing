namespace DancePlatform.API.Models;

/// <summary>
/// One edge of a roadmap's skill tree: <see cref="StepId"/> depends on
/// <see cref="PrerequisiteStepId"/>. Both sides always belong to the same roadmap — the seeder
/// resolves prerequisite keys within one file, so an edge can never cross styles.
/// </summary>
public class RoadmapStepPrerequisite
{
    public int StepId { get; set; }
    public RoadmapStep Step { get; set; } = null!;

    public int PrerequisiteStepId { get; set; }
    public RoadmapStep PrerequisiteStep { get; set; } = null!;
}
