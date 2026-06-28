using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users => Set<User>();
    public DbSet<Dance> Dances => Set<Dance>();
    public DbSet<Style> Styles => Set<Style>();
    public DbSet<MusicalStyle> MusicalStyles => Set<MusicalStyle>();
    public DbSet<Video> Videos => Set<Video>();
    public DbSet<VideoSegment> VideoSegments => Set<VideoSegment>();
    public DbSet<UserVideoLoop> UserVideoLoops => Set<UserVideoLoop>();
    public DbSet<DanceStyle> DanceStyles => Set<DanceStyle>();
    public DbSet<DanceMusicalStyle> DanceMusicalStyles => Set<DanceMusicalStyle>();
    public DbSet<UserFavoriteDance> UserFavoriteDances => Set<UserFavoriteDance>();
    public DbSet<UserLearnedDance> UserLearnedDances => Set<UserLearnedDance>();
    public DbSet<UserInProgressDance> UserInProgressDances => Set<UserInProgressDance>();
    public DbSet<UserMyStyle> UserMyStyles => Set<UserMyStyle>();
    public DbSet<VideoRating> VideoRatings => Set<VideoRating>();
    public DbSet<PracticeSession> PracticeSessions => Set<PracticeSession>();
    public DbSet<PracticeSessionItem> PracticeSessionItems => Set<PracticeSessionItem>();
    public DbSet<Instructor> Instructors => Set<Instructor>();
    public DbSet<DanceInstructor> DanceInstructors => Set<DanceInstructor>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Slugs are unique PER STYLE, not globally — the same step name in two different styles keeps
        // the same clean slug, disambiguated by the {styleSlug} URL segment (see DanceService). A
        // non-unique index still backs the /dances/{style}/{slug} lookup; uniqueness is enforced in
        // app code (GenerateUniqueSlugAsync) scoped to the dance's styles.
        modelBuilder.Entity<Dance>()
            .HasIndex(d => d.Slug);

        modelBuilder.Entity<VideoSegment>()
            .HasOne(vs => vs.Video)
            .WithMany(v => v.Segments)
            .HasForeignKey(vs => vs.VideoId)
            .OnDelete(DeleteBehavior.Cascade);

        // Personal loops: removed when either the owning user or the video is deleted.
        modelBuilder.Entity<UserVideoLoop>()
            .HasOne(l => l.User)
            .WithMany()
            .HasForeignKey(l => l.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<UserVideoLoop>()
            .HasOne(l => l.Video)
            .WithMany()
            .HasForeignKey(l => l.VideoId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<UserVideoLoop>()
            .HasIndex(l => new { l.UserId, l.VideoId });

        modelBuilder.Entity<DanceStyle>()
            .HasKey(ds => new { ds.DanceId, ds.StyleId });

        modelBuilder.Entity<DanceStyle>()
            .HasOne(ds => ds.Dance)
            .WithMany(d => d.DanceStyles)
            .HasForeignKey(ds => ds.DanceId);

        modelBuilder.Entity<DanceStyle>()
            .HasOne(ds => ds.Style)
            .WithMany(s => s.DanceStyles)
            .HasForeignKey(ds => ds.StyleId);

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasKey(dms => new { dms.DanceId, dms.MusicalStyleId });

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasOne(dms => dms.Dance)
            .WithMany(d => d.DanceMusicalStyles)
            .HasForeignKey(dms => dms.DanceId);

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasOne(dms => dms.MusicalStyle)
            .WithMany(ms => ms.DanceMusicalStyles)
            .HasForeignKey(dms => dms.MusicalStyleId);

        modelBuilder.Entity<UserFavoriteDance>()
            .HasKey(ufd => new { ufd.UserId, ufd.DanceId });

        modelBuilder.Entity<UserFavoriteDance>()
            .HasOne(ufd => ufd.User)
            .WithMany(u => u.FavoriteDances)
            .HasForeignKey(ufd => ufd.UserId);

        modelBuilder.Entity<UserFavoriteDance>()
            .HasOne(ufd => ufd.Dance)
            .WithMany(d => d.FavoritedBy)
            .HasForeignKey(ufd => ufd.DanceId);

        modelBuilder.Entity<UserLearnedDance>()
            .HasKey(uld => new { uld.UserId, uld.DanceId });

        modelBuilder.Entity<UserLearnedDance>()
            .HasOne(uld => uld.User)
            .WithMany(u => u.LearnedDances)
            .HasForeignKey(uld => uld.UserId);

        modelBuilder.Entity<UserLearnedDance>()
            .HasOne(uld => uld.Dance)
            .WithMany(d => d.LearnedBy)
            .HasForeignKey(uld => uld.DanceId);

        modelBuilder.Entity<UserInProgressDance>()
            .HasKey(uid => new { uid.UserId, uid.DanceId });

        modelBuilder.Entity<UserInProgressDance>()
            .HasOne(uid => uid.User)
            .WithMany(u => u.InProgressDances)
            .HasForeignKey(uid => uid.UserId);

        modelBuilder.Entity<UserInProgressDance>()
            .HasOne(uid => uid.Dance)
            .WithMany(d => d.InProgressBy)
            .HasForeignKey(uid => uid.DanceId);

        modelBuilder.Entity<UserMyStyle>()
            .HasKey(ums => new { ums.UserId, ums.StyleId });

        modelBuilder.Entity<UserMyStyle>()
            .HasOne(ums => ums.User)
            .WithMany(u => u.MyStyles)
            .HasForeignKey(ums => ums.UserId);

        modelBuilder.Entity<UserMyStyle>()
            .HasOne(ums => ums.Style)
            .WithMany(s => s.MyStyleUsers)
            .HasForeignKey(ums => ums.StyleId);

        // Usernames are unique case-INSENSITIVELY, enforced by a functional unique index on
        // LOWER("Username") created in the migration (EF's fluent model can't express a functional
        // index). A plain non-unique index still backs exact lookups; login/register compare on
        // LOWER(...) so "Justas" and "justas" are the same account.
        modelBuilder.Entity<User>()
            .HasIndex(u => u.Username);

        modelBuilder.Entity<VideoRating>()
            .HasKey(vr => new { vr.UserId, vr.VideoId });

        modelBuilder.Entity<VideoRating>()
            .HasOne(vr => vr.User)
            .WithMany(u => u.Ratings)
            .HasForeignKey(vr => vr.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<VideoRating>()
            .HasOne(vr => vr.Video)
            .WithMany(v => v.Ratings)
            .HasForeignKey(vr => vr.VideoId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<PracticeSession>()
            .HasOne(ps => ps.User)
            .WithMany(u => u.PracticeSessions)
            .HasForeignKey(ps => ps.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        // Finding the user's live session keys off (UserId, LastActivityAt) on every heartbeat.
        modelBuilder.Entity<PracticeSession>()
            .HasIndex(ps => new { ps.UserId, ps.LastActivityAt });

        modelBuilder.Entity<PracticeSessionItem>()
            .HasOne(pi => pi.Session)
            .WithMany(ps => ps.Items)
            .HasForeignKey(pi => pi.PracticeSessionId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<PracticeSessionItem>()
            .HasOne(pi => pi.Dance)
            .WithMany(d => d.PracticeItems)
            .HasForeignKey(pi => pi.DanceId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<PracticeSessionItem>()
            .HasIndex(pi => new { pi.PracticeSessionId, pi.DanceId });

        modelBuilder.Entity<DanceInstructor>()
            .HasKey(di => new { di.DanceId, di.InstructorId });

        modelBuilder.Entity<DanceInstructor>()
            .HasOne(di => di.Dance)
            .WithMany(d => d.DanceInstructors)
            .HasForeignKey(di => di.DanceId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<DanceInstructor>()
            .HasOne(di => di.Instructor)
            .WithMany(i => i.DanceInstructors)
            .HasForeignKey(di => di.InstructorId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
