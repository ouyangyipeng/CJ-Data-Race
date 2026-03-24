// case27: lambda表达式spawn竞争测试
// 测试lambda表达式直接作为spawn参数的场景

main() {
    var shared: Int64 = 0
    
    // lambda表达式直接spawn
    spawn { =>
        shared = shared + 1  // 写操作
    }
    
    spawn { =>
        shared = shared + 2  // 写操作
    }
}