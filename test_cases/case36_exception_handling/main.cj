// case36: 异常处理中的竞争测试
// 测试try-catch块中的数据竞争

main() {
    var shared: Int64 = 0
    var status: String = "init"
    
    spawn {
        try {
            shared = shared + 1  // 写操作
            status = "processing"  // 写操作
        } catch (e: Exception) {
            status = "error"  // 写操作
        }
    }
    
    spawn {
        try {
            shared = shared + 2  // 写操作
            status = "done"  // 写操作
        } catch (e: Exception) {
            status = "error2"  // 写操作
        }
    }
}