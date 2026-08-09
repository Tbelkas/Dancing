using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddRoadmapStepModule : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "ChildRoadmapId",
                table: "RoadmapSteps",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_RoadmapSteps_ChildRoadmapId",
                table: "RoadmapSteps",
                column: "ChildRoadmapId",
                unique: true,
                filter: "\"ChildRoadmapId\" IS NOT NULL");

            migrationBuilder.AddForeignKey(
                name: "FK_RoadmapSteps_Roadmaps_ChildRoadmapId",
                table: "RoadmapSteps",
                column: "ChildRoadmapId",
                principalTable: "Roadmaps",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_RoadmapSteps_Roadmaps_ChildRoadmapId",
                table: "RoadmapSteps");

            migrationBuilder.DropIndex(
                name: "IX_RoadmapSteps_ChildRoadmapId",
                table: "RoadmapSteps");

            migrationBuilder.DropColumn(
                name: "ChildRoadmapId",
                table: "RoadmapSteps");
        }
    }
}
