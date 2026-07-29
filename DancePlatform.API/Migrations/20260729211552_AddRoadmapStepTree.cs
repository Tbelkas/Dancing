using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddRoadmapStepTree : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Key",
                table: "RoadmapSteps",
                type: "text",
                nullable: false,
                defaultValue: "");

            migrationBuilder.CreateTable(
                name: "RoadmapStepPrerequisites",
                columns: table => new
                {
                    StepId = table.Column<int>(type: "integer", nullable: false),
                    PrerequisiteStepId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_RoadmapStepPrerequisites", x => new { x.StepId, x.PrerequisiteStepId });
                    table.ForeignKey(
                        name: "FK_RoadmapStepPrerequisites_RoadmapSteps_PrerequisiteStepId",
                        column: x => x.PrerequisiteStepId,
                        principalTable: "RoadmapSteps",
                        principalColumn: "Id");
                    table.ForeignKey(
                        name: "FK_RoadmapStepPrerequisites_RoadmapSteps_StepId",
                        column: x => x.StepId,
                        principalTable: "RoadmapSteps",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_RoadmapStepPrerequisites_PrerequisiteStepId",
                table: "RoadmapStepPrerequisites",
                column: "PrerequisiteStepId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "RoadmapStepPrerequisites");

            migrationBuilder.DropColumn(
                name: "Key",
                table: "RoadmapSteps");
        }
    }
}
