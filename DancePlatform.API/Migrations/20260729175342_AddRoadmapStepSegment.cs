using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddRoadmapStepSegment : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "VideoSegmentId",
                table: "RoadmapSteps",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_RoadmapSteps_VideoSegmentId",
                table: "RoadmapSteps",
                column: "VideoSegmentId");

            migrationBuilder.AddForeignKey(
                name: "FK_RoadmapSteps_VideoSegments_VideoSegmentId",
                table: "RoadmapSteps",
                column: "VideoSegmentId",
                principalTable: "VideoSegments",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_RoadmapSteps_VideoSegments_VideoSegmentId",
                table: "RoadmapSteps");

            migrationBuilder.DropIndex(
                name: "IX_RoadmapSteps_VideoSegmentId",
                table: "RoadmapSteps");

            migrationBuilder.DropColumn(
                name: "VideoSegmentId",
                table: "RoadmapSteps");
        }
    }
}
