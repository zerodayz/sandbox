package main

import (
	"fmt"
	"os"
	"os/exec"
	"time"
)

func runTargetScript(scriptPath string) (float64, error) {
	start := time.Now()
	cmd := exec.Command("go", "run", scriptPath)
	cmd.Stdout = nil
	cmd.Stderr = nil
	if err := cmd.Run(); err != nil {
		return 0, err
	}
	elapsed := time.Since(start).Seconds()
	return elapsed, nil
}

func main() {
	if len(os.Args) != 2 {
		fmt.Println("Usage: go run benchmark.go <scriptPath>")
		os.Exit(1)
	}

	scriptPath := os.Args[1]
	elapsed, err := runTargetScript(scriptPath)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("%.3f", elapsed)
}
