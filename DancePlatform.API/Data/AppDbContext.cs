using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users => Set<User>();
    public DbSet<UserLogin> UserLogins => Set<UserLogin>();
    public DbSet<Dance> Dances => Set<Dance>();
    public DbSet<Style> Styles => Set<Style>();
    public DbSet<MusicalStyle> MusicalStyles => Set<MusicalStyle>();
    public DbSet<Video> Videos => Set<Video>();
    public DbSet<VideoSegment> VideoSegments => Set<VideoSegment>();
    public DbSet<UserVideoLoop> UserVideoLoops => Set<UserVideoLoop>();
    public DbSet<VideoNote> VideoNotes => Set<VideoNote>();
    public DbSet<UserChoreo> UserChoreos => Set<UserChoreo>();
    public DbSet<UserChoreoLoop> UserChoreoLoops => Set<UserChoreoLoop>();
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
    public DbSet<Roadmap> Roadmaps => Set<Roadmap>();
    public DbSet<RoadmapStage> RoadmapStages => Set<RoadmapStage>();
    public DbSet<RoadmapStep> RoadmapSteps => Set<RoadmapStep>();
    public DbSet<RoadmapStepPrerequisite> RoadmapStepPrerequisites => Set<RoadmapStepPrerequisite>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        // Slugs are unique PER STYLE, not globally — the same step name in two different styles keeps
        // the same clean slug, disambiguated by the {styleSlug} URL segment (see DanceService). A
        // non-unique index still backs the /dances/{style}/{slug} lookup; uniqueness is enforced in
        // app code (GenerateUniqueSlugAsync) scoped to the dance's styles.
        modelBuilder.Entity<Dance>()
            .HasIndex(d => d.Slug);

        // --- Intake quarantine -------------------------------------------------
        // A video only reaches a query once it is approved. This is a GLOBAL filter
        // on purpose: Dance.Videos is read directly by DanceService (counts,
        // thumbnails, sort order), RoadmapService and PracticeService, so filtering
        // at each call site would eventually miss one and leak a pending video onto
        // the public site. Admin paths that must reach held-back rows call
        // IgnoreQueryFilters() explicitly.
        //
        // The four dependents below carry the matching filter because they have a
        // required relationship to Video; without it EF warns, and their rows would
        // otherwise survive a query whose principal was filtered away.
        modelBuilder.Entity<Video>()
            .HasQueryFilter(v => v.ReviewState == "approved");
        modelBuilder.Entity<VideoSegment>()
            .HasQueryFilter(s => s.Video.ReviewState == "approved");
        modelBuilder.Entity<VideoRating>()
            .HasQueryFilter(r => r.Video.ReviewState == "approved");
        modelBuilder.Entity<VideoNote>()
            .HasQueryFilter(n => n.Video.ReviewState == "approved");
        modelBuilder.Entity<UserVideoLoop>()
            .HasQueryFilter(l => l.Video.ReviewState == "approved");

        modelBuilder.Entity<Video>()
            .HasIndex(v => v.ReviewState);

        modelBuilder.Entity<VideoSegment>()
            .HasOne(vs => vs.Video)
            .WithMany(v => v.Segments)
            .HasForeignKey(vs => vs.VideoId)
            .OnDelete(DeleteBehavior.Cascade);

        // Personal videos: a user's private additions are removed when their account is deleted;
        // null OwnerUserId means the video is global. Indexed so the global-or-own visibility
        // filter (VideoService) stays cheap.
        modelBuilder.Entity<Video>()
            .HasOne(v => v.Owner)
            .WithMany()
            .HasForeignKey(v => v.OwnerUserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<Video>()
            .HasIndex(v => v.OwnerUserId);

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

        // Personal timestamped notes: same lifecycle as loops — gone when the
        // owning user or the video goes.
        modelBuilder.Entity<VideoNote>()
            .HasOne(n => n.User)
            .WithMany()
            .HasForeignKey(n => n.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<VideoNote>()
            .HasOne(n => n.Video)
            .WithMany()
            .HasForeignKey(n => n.VideoId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<VideoNote>()
            .HasIndex(n => new { n.UserId, n.VideoId });

        // Local choreos: the video file stays on the user's machine; these rows hold only
        // its file name and the user's saved time slots. Everything dies with the account.
        modelBuilder.Entity<UserChoreo>()
            .HasOne(c => c.User)
            .WithMany()
            .HasForeignKey(c => c.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<UserChoreo>()
            .HasIndex(c => c.UserId);

        modelBuilder.Entity<UserChoreoLoop>()
            .HasOne(l => l.Choreo)
            .WithMany(c => c.Loops)
            .HasForeignKey(l => l.UserChoreoId)
            .OnDelete(DeleteBehavior.Cascade);

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

        // External sign-in methods die with the account they belong to.
        modelBuilder.Entity<UserLogin>()
            .HasOne(l => l.User)
            .WithMany(u => u.Logins)
            .HasForeignKey(l => l.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        // The identity constraint of the whole feature: one provider subject maps to exactly one
        // account. Without uniqueness here, a race on the callback could mint two accounts for the
        // same Google user, and the second sign-in would pick between them arbitrarily.
        modelBuilder.Entity<UserLogin>()
            .HasIndex(l => new { l.Provider, l.ProviderUserId })
            .IsUnique();

        // Backs the "which providers is this account linked to?" lookup on the profile page.
        modelBuilder.Entity<UserLogin>()
            .HasIndex(l => l.UserId);

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

        // Deleting a video must not erase the practice time it generated — just drop the attribution.
        modelBuilder.Entity<PracticeSessionItem>()
            .HasOne(pi => pi.Video)
            .WithMany()
            .HasForeignKey(pi => pi.VideoId)
            .OnDelete(DeleteBehavior.SetNull);

        // Same for local choreos: removing one keeps its practice time, shown as "Removed choreo".
        modelBuilder.Entity<PracticeSessionItem>()
            .HasOne(pi => pi.Choreo)
            .WithMany()
            .HasForeignKey(pi => pi.UserChoreoId)
            .OnDelete(DeleteBehavior.SetNull);

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

        // Roadmaps are addressed by slug, like dances. The index stays global rather than
        // per-owner so /roadmaps/{slug} resolves without knowing whose path it is — the service
        // uniquifies a personal tree's slug on create instead.
        modelBuilder.Entity<Roadmap>()
            .HasIndex(r => r.Slug)
            .IsUnique();

        modelBuilder.Entity<Roadmap>()
            .HasOne(r => r.Style)
            .WithMany()
            .HasForeignKey(r => r.StyleId)
            .OnDelete(DeleteBehavior.Cascade);

        // Null owner = a curated path. Cascade: a personal tree is the user's own data and has
        // no meaning once the account is gone.
        modelBuilder.Entity<Roadmap>()
            .HasOne(r => r.Owner)
            .WithMany()
            .HasForeignKey(r => r.OwnerUserId)
            .OnDelete(DeleteBehavior.Cascade);

        // The index's split into "mine" and "everyone's" runs on this every page load.
        modelBuilder.Entity<Roadmap>()
            .HasIndex(r => r.OwnerUserId);

        modelBuilder.Entity<RoadmapStage>()
            .HasOne(s => s.Roadmap)
            .WithMany(r => r.Stages)
            .HasForeignKey(s => s.RoadmapId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<RoadmapStep>()
            .HasOne(s => s.Stage)
            .WithMany(st => st.Steps)
            .HasForeignKey(s => s.RoadmapStageId)
            .OnDelete(DeleteBehavior.Cascade);

        // Deleting a dance must not tear a hole in the path — the step stays and falls back to
        // its authored title, exactly like a step whose move isn't in the catalog yet.
        modelBuilder.Entity<RoadmapStep>()
            .HasOne(s => s.Dance)
            .WithMany()
            .HasForeignKey(s => s.DanceId)
            .OnDelete(DeleteBehavior.SetNull);

        modelBuilder.Entity<RoadmapStepPrerequisite>()
            .HasKey(p => new { p.StepId, p.PrerequisiteStepId });

        modelBuilder.Entity<RoadmapStepPrerequisite>()
            .HasOne(p => p.Step)
            .WithMany(s => s.Prerequisites)
            .HasForeignKey(p => p.StepId)
            .OnDelete(DeleteBehavior.Cascade);

        // NoAction on this side: two cascade paths into the same table is more than Postgres
        // will accept, and it isn't needed — the seeder drops every edge before rebuilding
        // steps, and deleting a roadmap cascades its steps (and therefore its edges) anyway.
        modelBuilder.Entity<RoadmapStepPrerequisite>()
            .HasOne(p => p.PrerequisiteStep)
            .WithMany()
            .HasForeignKey(p => p.PrerequisiteStepId)
            .OnDelete(DeleteBehavior.NoAction);

        // Segments are rebuilt wholesale by the chip scripts, so their ids are not stable —
        // the seeder re-resolves this from the authored label each boot. SetNull keeps a
        // re-chipped video from deleting the step; it just widens back to the whole dance.
        modelBuilder.Entity<RoadmapStep>()
            .HasOne(s => s.VideoSegment)
            .WithMany()
            .HasForeignKey(s => s.VideoSegmentId)
            .OnDelete(DeleteBehavior.SetNull);

        // A step can point at a whole nested roadmap (a "module"). SetNull, not Cascade: if the
        // module is deleted the gateway step survives as a plain unlinked step, the same way a
        // step outlives its dance. Cascade here would also be a second cascade path from
        // Roadmap into RoadmapSteps (the first runs through RoadmapStages), which Postgres
        // rejects outright.
        modelBuilder.Entity<RoadmapStep>()
            .HasOne(s => s.ChildRoadmap)
            .WithMany()
            .HasForeignKey(s => s.ChildRoadmapId)
            .OnDelete(DeleteBehavior.SetNull);

        // At most one step may claim a given module. Filtered, because the overwhelming majority
        // of steps have no child and NULLs must not collide. This is what makes "which path does
        // this module belong to?" — the breadcrumb — a single unambiguous answer.
        modelBuilder.Entity<RoadmapStep>()
            .HasIndex(s => s.ChildRoadmapId)
            .IsUnique()
            .HasFilter("\"ChildRoadmapId\" IS NOT NULL");
    }
}
