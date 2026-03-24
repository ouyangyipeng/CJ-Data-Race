// 测试用例11: 逃逸变量
// 变量被spawn捕获，跨线程访问存在竞争

main() {
    var counter: Int64 = 0
    
    // 变量counter被spawn捕获，成为共享变量
    spawn {
        counter = counter + 1  // 写操作
    }
    
    // 另一个spawn也捕获counter
    spawn {
        counter = counter + 1  // 写操作，存在竞争
    }
    
    println(counter)
}