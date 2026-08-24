using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <summary>
    /// Flip the database-level default for Videos.ReviewState from "approved" to
    /// "pending", so the safe state is the one you get by forgetting.
    ///
    /// The seeding scripts insert with raw SQL and never name this column, which is
    /// exactly the path that produced the documented garbage. Leaving the default at
    /// "approved" would publish every future bulk-seeded video the moment it landed.
    ///
    /// This does not affect the API: the Video model initialises ReviewState to
    /// "approved", so EF always sends an explicit value and hand-added videos stay
    /// visible immediately. Only an INSERT that omits the column is quarantined.
    ///
    /// Existing rows are untouched - a column default applies to new inserts only.
    /// </summary>
    public partial class QuarantineRawInsertsByDefault : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                @"ALTER TABLE ""Videos"" ALTER COLUMN ""ReviewState"" SET DEFAULT 'pending';");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(
                @"ALTER TABLE ""Videos"" ALTER COLUMN ""ReviewState"" SET DEFAULT 'approved';");
        }
    }
}
