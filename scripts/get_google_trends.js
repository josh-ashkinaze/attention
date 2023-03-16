/**
Author: Joshua Ashkinaze

Fetches the Google Trends data for a given keyword (kw) within a specified date range
(start_date and end_date) and outputs a JSON array of objects containing the keyword,
interest value, and date for each day in the date range.
@param {string} kw - The keyword to fetch Google Trends data for.
@param {string} start_date - The start date for the date range (inclusive), in the format "YYYY-MM-DD".
@param {string} end_date - The end date for the date range (inclusive), in the format "YYYY-MM-DD".
@example
// Fetch Google Trends data for "Node.js" between March 1, 2023, and March 15, 2023
fetchInterestOverTime("Node.js", "2023-03-01", "2023-03-15");
@returns {void}
@output
// JSON array of objects containing keyword, value, and date
[
{"kw": "Node.js", "value": 68, "date": "2023-03-01"},
{"kw": "Node.js", "value": 65, "date": "2023-03-02"},
...
]
*/

const googleTrends = require('google-trends-api');

async function fetchInterestOverTime(kw, start_date, end_date) {
  try {
    const data = await googleTrends.interestOverTime({
      keyword: kw,
      startTime: new Date(start_date),
      endTime: new Date(end_date),
    });

    const parsedData = JSON.parse(data).default.timelineData;
    const results = parsedData.map(item => {
      return {
        kw: kw,
        value: item.value[0],
        date: new Date(item.time * 1000).toISOString().slice(0, 10),
      };
    });

    console.log(JSON.stringify(results));
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

// Retrieve command-line arguments
const args = process.argv.slice(2);
if (args.length < 3) {
  console.log("Usage: node gtrends.js <keyword> <start_date> <end_date>");
  process.exit(1);
}

const [kw, start_date, end_date] = args;

fetchInterestOverTime(kw, start_date, end_date);
