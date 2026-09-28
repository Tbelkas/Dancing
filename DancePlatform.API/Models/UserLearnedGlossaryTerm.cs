namespace DancePlatform.API.Models;

/// <summary>
/// A glossary move the user has marked learned. Its own table rather than reusing
/// <see cref="UserLearnedDance"/>: most terms have no catalog dance behind them, and one dance
/// can back several terms, so borrowing the dance's flag would tick moves the user never marked.
/// </summary>
public class UserLearnedGlossaryTerm
{
    public int UserId { get; set; }
    public User User { get; set; } = null!;

    public int GlossaryTermId { get; set; }
    public GlossaryTerm GlossaryTerm { get; set; } = null!;

    public DateTime DateAdded { get; set; } = DateTime.UtcNow;
}
